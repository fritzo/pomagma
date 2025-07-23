# Design Doc: Inference Scheduling

## Objective

Speed up inference in the surveyor by reducing cleanup overhead and improving parallel efficiency.

## Background

### Architecture Overview

Pomagma implements two primary inference engines: the **surveyor** for forward-chaining database construction and the **cartographer** for scalable batch operations. The surveyor operates on **micro atlases** (16-bit identifiers, up to 65K E-classes) optimized for concurrent write-heavy growth, while the cartographer uses **macro atlases** (32-bit identifiers) optimized for read-heavy batch processing and aggregation.

### Inference Types and Completeness

The system implements three distinct types of inference with different completeness guarantees:

#### 1. Incremental Inference via GIVEN Tasks (Complete)

**GIVEN tasks** are event-driven inference programs triggered immediately when database events occur. The virtual machine maintains an event-driven dispatch system through the `Agenda` class (`/pomagma/atlas/vm.hpp`), where insertion of any fact triggers all applicable GIVEN programs:

- `GIVEN_EXISTS`: Triggered on object creation
- `GIVEN_UNARY_RELATION`: Triggered on unary relation insertion
- `GIVEN_BINARY_RELATION`: Triggered on binary relation insertion  
- `GIVEN_BINARY_FUNCTION`: Triggered on binary function definition
- `GIVEN_SYMMETRIC_FUNCTION`: Triggered on symmetric function definition

The scheduler (`/pomagma/atlas/micro/scheduler.cpp`) manages concurrent task queues with strict priority ordering:

1. **MergeTask** (exclusive, highest priority) - Object equivalence handling
2. **Enforce Tasks** (high priority) - Event-driven inference (ExistsTask, PositiveOrderTask, UnaryRelationTask, etc.)
3. **AssumeTask** (initialization) - Loading initial facts from theory files
4. **SampleTask** (background) - Random object generation
5. **CleanupTask** (background) - Maintenance programs

Incremental inference would be **complete** if run sequentially because every insertion event triggers all applicable inference rules before the insertion operation completes, ensuring all direct consequences are derived.
However the surveyor runs in parallel under `std::memory_order::relaxed` semantics, leading to possible stale reads, breaking completeness.
For this reason incremental inference is followed by a phase of cleanup inference.

#### 2. Cleanup Inference via Tasks (Complete)

**Cleanup tasks** handle complex multi-event inference rules that cannot be efficiently triggered by single database events. They run periodically through the `Cleanup` namespace in the scheduler using atomic counters (`g_type`, `g_done_count`) for lock-free round-robin distribution across cleanup types.

The cleanup system has two categories managed by the `Agenda` class:
- **Small Cleanup Tasks** (`m_cleanup_small`) - Execute once per cycle
- **Large Cleanup Tasks** (`m_cleanup_large`) - Execute in parallel blocks

Cleanup inference is **complete** because it systematically examines all combinations of facts that could trigger inference rules, providing complete coverage regardless of the order facts were originally inserted.

#### 3. Batch Inference (Incomplete)

**Batch inference** implements specialized algorithms for mathematical properties too expensive to handle incrementally. The cartographer implements many batch rules in `/pomagma/cartographer/infer.cpp`, whereas the surveyor implements only `infer_nless()` in `/pomagma/surveyor/infer.cpp`, which handles NLESS monotonicity rules.

When incremental inference accumulates too many negative ordering tasks (threshold: `POMAGMA_NLESS_MONOTONE_THRESHOLD`, default 1000), the surveyor switches to parallel batch processing using OpenMP:
```cpp
#pragma omp parallel
{
    DenseSet y_set(item_dim);
    DenseSet z_set(item_dim);
    size_t local_count = 0;
    
#pragma omp for schedule(dynamic, 1)
    for (Ob x = 1; x <= item_dim; ++x) {
        // Parallel transitivity inference across all objects
    }
    theorem_count.fetch_add(local_count, std::memory_order_acq_rel);
}
```
(Currently the surveyor's batch inference is redundant because it follows the cleanup phase, but it may become useful if the cleanup phase can be eliminated.)

Batch inference is **incomplete** by design - it only implements specific, hand-optimized algorithms for particular inference patterns (mainly NLESS monotonicity and transitivity), trading logical completeness for computational tractability.

### Surveyor vs Cartographer: Growth Models and Saturation

The **surveyor only grows** through monotonic addition of facts and objects. When contradictions are discovered, objects are merged rather than deleted, preserving all information while maintaining consistency. The surveyor implements **complete inference** through the combination of incremental GIVEN tasks and systematic cleanup phases, always resulting in a saturated database.

The **cartographer can truncate, grow, and merge** databases. It implements three key operations:

1. **Truncate** (`/pomagma/cartographer/trim.cpp`): Creates smaller E-graphs by probabilistically selecting important E-classes using language models
2. **Grow**: Extends E-graphs through controlled VM program execution  
3. **Merge** (`/pomagma/cartographer/aggregate.cpp`): Combines multiple survey results using thread-parallel injection

The cartographer implements only **incomplete batch inference**. Its rule set in `/pomagma/cartographer/infer.cpp` has explicit limitations - line 225 contains `// FIXME this implementation is not complete for the above rules` referring to incomplete LESS-monotonicity rule coverage. When the cartographer merges two databases, **results may not be saturated** because:

- No post-merge complete inference is performed
- Mapping conflicts between different source databases aren't fully resolved
- The incomplete rule application means even running inference after merge doesn't achieve full saturation
- Performance trade-offs prioritize throughput over completeness for large-scale operations

### Parallel Processing and Memory Ordering

The surveyor's incremental rules use **relaxed atomics** for performance in the concurrent task system. Task statistics use relaxed memory ordering:

```cpp
std::atomic<uint_fast64_t> m_schedule_count;
std::atomic<uint_fast64_t> m_execute_count;
void schedule() { m_schedule_count.fetch_add(1, std::memory_order_relaxed); }
```

However, batch inference coordination uses stronger **acquire-release semantics**:

```cpp
theorem_count.fetch_add(local_count, std::memory_order_acq_rel);
```

This **relaxed atomics approach may be incomplete in parallel settings** because timing issues between concurrent threads can cause some inference opportunities to be missed during the initial incremental phase. The surveyor addresses this by adding a **cleanup phase after incremental tasks**, ensuring the system always results in a saturated database despite the potential incompleteness of the relaxed atomic incremental phase.

### Storage Architecture Differences

The **micro atlas** (surveyor) uses tiled atomic arrays (8×8 tiles of 64 elements) for cache-optimized concurrent access with lock-free operations using `std::atomic<Ob>` and acquire/release semantics. This architecture is optimized for write-heavy concurrent E-graph growth.

The **macro atlas** (cartographer) uses hash maps (`ObPairMap`) for binary function storage with simple mutex-based synchronization (`std::mutex m_raw_mutex`), optimized for read-heavy batch operations and aggregation.

### Workflow Integration

The typical workflow combines both engines:
1. **Surveyor** explores regions → creates **Charts** (saturated E-graphs).
2. **Cartographer** aggregates Charts → produces larger **E-graphs** for **Analyst** querying.
3. Charts from surveyor are guaranteed to be saturated; aggregated results from cartographer may not be fully saturated.

This division of labor allows the system to benefit from both complete inference (surveyor) for correctness and scalable processing (cartographer) for performance on large datasets.

## Design Overview

The design focuses on three main optimizations to reduce surveyor cleanup overhead:

1. **Reduce cleanup work** by refactoring the surveyor incremental scheduler to use acquire-release semantics and a phased/BSP (Bulk Synchronous Parallel) workflow. This eliminates the need for a final cleanup phase by ensuring incremental inference is complete.

2. **Avoid initial cleanup work** for rules implemented in the cartographer by detecting when databases have already been processed by the cartographer's rule set.
This requires the compiler to add `IF_GLOBAL` guards to cleanup rules that are known to be implemented in the cartographer.

3. **Track saturation status** and avoid initial cleanup phase if a database is already saturated (e.g. if it is not the result of a merger). Since saturation depends on the ruleset, we need to track rule sets. The main source of non-saturation is when the cartographer merges databases then only partially saturates them with respect to its incomplete rule set.

## Design Details

### Surveyor scheduler redesign

The redesigned scheduler addresses the fundamental completeness issues by implementing **BSP-style partial total ordering** with relaxed atomics and **work stealing** for performance. The key insight is that we need strict ordering between phases for correctness, but within each phase, task execution order doesn't matter, eliminating the need for FIFO queues.

#### Core Design Principles

**BSP-style Partial Total Ordering**: The scheduler enforces that all tasks in phase N complete before any task in phase N+1 begins, ensuring completeness without requiring global sequential ordering within phases.

**Relaxed Memory Ordering with Barriers**: With full barriers between phases, database operations can use `std::memory_order_relaxed` for performance, since the barriers provide necessary synchronization points. Only the barriers themselves need acquire-release semantics.

**Double-Buffer with Work Stealing**: Use ping-pong queues for phase transitions and work stealing within each phase for optimal load balancing.

#### Hybrid Double-Buffer + Work Stealing Architecture

The new scheduler combines ping-pong queues for phase management with work stealing for load balancing:

```cpp
class HybridScheduler {
private:
    // Double-buffered per-thread work deques  
    std::vector<std::array<WorkStealingDeque<Task>, 2>> thread_deques;
    
    // Current buffer indices (ping-pong between 0 and 1)
    std::atomic<int> read_buffer{0};
    std::atomic<int> write_buffer{1};
    
    // Phase synchronization
    ThreadBarrier phase_barrier;
    const int num_threads;

public:
    // Schedule task to current write buffer
    template<typename TaskType>
    void schedule_task(TaskType&& task, int thread_id) {
        int write_idx = write_buffer.load(std::memory_order_relaxed);
        thread_deques[thread_id][write_idx].push_bottom(task);
    }
    
    // Worker thread main loop
    void worker_loop(int thread_id) {
        while (true) {
            int read_idx = read_buffer.load(std::memory_order_relaxed);
            
            // Phase 1: Execute local tasks from read buffer
            while (auto task = thread_deques[thread_id][read_idx].pop_bottom()) {
                execute_task(*task);
                
                // New tasks go to write buffer for next phase
                schedule_generated_tasks(task->generated_tasks, thread_id);
            }
            
            // Phase 2: Steal work from other threads' read buffers
            for (int steal_attempts = 0; steal_attempts < num_threads; ++steal_attempts) {
                int victim = (thread_id + steal_attempts + 1) % num_threads;
                if (auto task = thread_deques[victim][read_idx].steal_top()) {
                    execute_task(*task);
                    schedule_generated_tasks(task->generated_tasks, thread_id);
                    break; // Found work, restart local processing
                }
            }
            
            // Phase 3: Wait for phase completion and buffer swap
            if (phase_barrier.wait()) {
                // Last thread: swap ping-pong buffers
                swap_buffers();
            }
        }
    }
    
private:
    void swap_buffers() {
        int old_read = read_buffer.load(std::memory_order_relaxed);
        int old_write = write_buffer.load(std::memory_order_relaxed);
        
        read_buffer.store(old_write, std::memory_order_relaxed);
        write_buffer.store(old_read, std::memory_order_relaxed);
    }
};
```

#### Cache-Friendly Data Structure Design

**Per-Thread Work Deques**: Each thread maintains a cache-line-aligned double-ended queue optimized for local LIFO scheduling and remote FIFO stealing:

```cpp
template<typename T>
class WorkStealingDeque {
private:
    // Cache-line aligned to prevent false sharing
    alignas(64) std::atomic<size_t> top{0};
    alignas(64) std::atomic<size_t> bottom{0};
    alignas(64) std::vector<std::atomic<T*>> buffer;
    
public:
    // Local thread pushes to bottom (LIFO for cache locality)
    void push_bottom(T* task) {
        size_t b = bottom.load(std::memory_order_relaxed);
        buffer[b % buffer.size()].store(task, std::memory_order_relaxed);
        bottom.store(b + 1, std::memory_order_release);
    }
    
    // Local thread pops from bottom (LIFO)
    T* pop_bottom() {
        size_t b = bottom.load(std::memory_order_relaxed);
        if (b == 0) return nullptr;
        
        b = b - 1;
        bottom.store(b, std::memory_order_relaxed);
        
        T* task = buffer[b % buffer.size()].load(std::memory_order_relaxed);
        
        size_t t = top.load(std::memory_order_acquire);
        if (t <= b) {
            return task;  // Common case: no contention
        }
        
        // Contention with steal - use acquire-release semantics
        bottom.store(b + 1, std::memory_order_relaxed);
        return nullptr;
    }
    
    // Remote threads steal from top (FIFO for work distribution)
    T* steal_top() {
        size_t t = top.load(std::memory_order_acquire);
        size_t b = bottom.load(std::memory_order_acquire);
        
        if (t >= b) return nullptr;  // Empty or contention
        
        T* task = buffer[t % buffer.size()].load(std::memory_order_relaxed);
        
        if (!top.compare_exchange_weak(t, t + 1, 
                                       std::memory_order_acq_rel,
                                       std::memory_order_relaxed)) {
            return nullptr;  // Race with another stealer
        }
        
        return task;
    }
};
```

#### Performance Optimizations

**NUMA-Aware Work Stealing**: Workers prefer to steal from their NUMA peers (same CPU or same chiplet).

**Batch work stealing**: Steal half the dequeue, not just a single task.

#### Implementation Strategy

1. **Replace TBB queues** with double-buffered work-stealing deques
2. **Add phase barriers** with ping-pong buffer swapping for BSP-style completion guarantees  
3. **Use work stealing within phases** for optimal load balancing
4. **Keep relaxed memory ordering** since barriers provide synchronization
5. **Optimize for common case** where cleanup phase becomes empty

The hybrid approach provides:
- **Clean phase separation** through ping-pong buffers (eliminates race conditions)
- **Load balancing** through work stealing within each phase  
- **Cache locality** through per-thread deques
- **Performance** through relaxed atomics with barrier synchronization

### Surveyor-Cartographer Workflows

The current workflow creates inefficiency when charts flow from cartographer to surveyor:

**Current inefficient pattern:**
1. Cartographer merges multiple charts → produces unsaturated result
2. Surveyor loads unsaturated chart → must run full cleanup phase  
3. Cleanup phase re-derives facts that could have been computed during merge

**Proposed optimization:**
Track which rules have been applied to each chart/database through metadata. When the surveyor loads a chart, it can skip cleanup for rules already applied by the cartographer. For rules unique to the surveyor (those requiring inverse tables unavailable in macro atlas), targeted cleanup can be performed.

**Trade-off analysis for stronger cartographer rules:**
- **Pro**: Stronger cartographer rules reduce surveyor cleanup overhead
- **Con**: More complex cartographer implementation increases memory usage and reduces batch processing throughput  
- **Assessment**: Merging is **necessary** for scalability - the alternative would require surveyor to handle charts too large for micro atlas (>65K E-classes)

### Stronger Rule Sets

The cartographer could potentially implement complete inference, eliminating the need for cleanup in the surveyor. However, the main challenge is **lack of inverse tables in pomagma/atlas/macro**. 

The macro atlas uses hash maps (`std::unordered_map<ObPair, Ob>`) for forward lookups but doesn't maintain reverse indices. Many inference rules require finding "all X such that f(X,Y) = Z" which requires expensive iteration over the entire hash map rather than efficient inverse lookups available in the micro atlas's tiled array structure.

**Proposed solution:** The `/pomagma/compiler` could optionally generate a set of complete cleanup rules that avoid inverse table usage. These rules would:

- Use forward iteration patterns instead of inverse lookups
- Implement the same logical completeness as surveyor rules  
- Be optimized for macro atlas's hash map storage
- Allow cartographer to produce fully saturated results

This would enable a workflow where:
1. Cartographer performs complete inference during merge operations
2. Surveyor can skip cleanup entirely for charts from cartographer
3. Only truly new inference (from incremental GIVEN tasks) requires cleanup

The implementation complexity would be moderate - the compiler already generates specialized versions of rules for different atlas types, so extending this to generate inverse-table-free complete rules is feasible.
