# Design Doc: Inference Scheduling

## Objective

Speed up inference in the surveyor by reducing cleanup overhead and improving parallel efficiency.

## Background

### Architecture Overview

Pomagma implements two primary inference engines: the **surveyor** for forward-chaining database construction and the **cartographer** for scalable batch operations. Both now operate on **16-bit identifiers** (up to 65K E-classes), with the surveyor using micro atlases optimized for concurrent write-heavy growth, while the cartographer uses macro atlases optimized for read-heavy batch processing and aggregation.

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

1. **Reduce cleanup work** by refactoring the surveyor incremental scheduler to use acquire-release semantics and a phased/BSP (Bulk Synchronous Parallel) workflow. This eliminates the need for a final cleanup phase by ensuring incremental inference is complete. *See [theorem_queue.md](theorem_queue.md) for the detailed implementation of phased inference using theorem queues.*

2. **Avoid initial cleanup work** for rules implemented in the cartographer by detecting when databases have already been processed by the cartographer's rule set.
This requires the compiler to add `IF_GLOBAL` guards to cleanup rules that are known to be implemented in the cartographer.

3. **Track saturation status** and avoid initial cleanup phase if a database is already saturated (e.g. if it is not the result of a merger). Since saturation depends on the ruleset, we need to track rule sets. The main source of non-saturation is when the cartographer merges databases then only partially saturates them with respect to its incomplete rule set.

## Design Details

### Surveyor scheduler redesign

The redesigned scheduler addresses the fundamental completeness issues by implementing **BSP-style partial total ordering** with relaxed atomics and **work stealing** for performance. The key insight is that we need strict ordering between phases for correctness, but within each phase, task execution order doesn't matter, eliminating the need for FIFO queues.

#### Core Design Principles

**BSP-style Partial Total Ordering**: The scheduler enforces that all tasks in phase N complete before any task in phase N+1 begins, ensuring completeness without requiring global sequential ordering within phases.

**Relaxed Memory Ordering with Barriers**: With full barriers between phases, database operations can use `std::memory_order_relaxed` for performance, since the barriers provide necessary synchronization points. Only the barriers themselves need acquire-release semantics.

**Double-Buffer with Work Redistribution and Stealing**: Use ping-pong queues for phase transitions, work redistribution at barriers for load balancing, and work stealing within phases for efficiency.

#### Phased Scheduler Architecture

The scheduler uses `uint64_t` tasks with double-buffered queues, combining work redistribution at barriers with work stealing within phases:

```cpp
class PhasedScheduler {
private:
    std::vector<std::array<std::vector<uint64_t>, 2>> thread_queues;
    std::atomic<int> read_buffer{0};
    std::atomic<int> write_buffer{1};
    ThreadBarrier phase_barrier;

public:
    void worker_loop(int thread_id) {
        while (true) {
            int read_idx = read_buffer.load(std::memory_order_relaxed);
            auto& my_tasks = thread_queues[thread_id][read_idx];
            
            // Process local tasks first
            for (uint64_t task : my_tasks) {
                execute_task(task, thread_id);
            }
            my_tasks.clear();
            
            // Steal work from other threads
            for (int victim = 0; victim < num_threads; ++victim) {
                if (victim == thread_id) continue;
                auto& victim_tasks = thread_queues[victim][read_idx];
                if (!victim_tasks.empty()) {
                    // Steal half the remaining work
                    size_t steal_count = victim_tasks.size() / 2;
                    for (size_t i = 0; i < steal_count; ++i) {
                        execute_task(victim_tasks.back(), thread_id);
                        victim_tasks.pop_back();
                    }
                }
            }
            
            // Barrier: last thread redistributes work and swaps buffers
            if (phase_barrier.wait()) {
                redistribute_and_swap();
            }
        }
    }
    
private:
    void redistribute_and_swap() {
        // Collect and redistribute work from write buffers
        std::vector<uint64_t> all_tasks;
        int write_idx = write_buffer.load(std::memory_order_relaxed);
        
        for (auto& thread_buffer : thread_queues) {
            auto& tasks = thread_buffer[write_idx];
            all_tasks.insert(all_tasks.end(), tasks.begin(), tasks.end());
            tasks.clear();
        }
        
        // Round-robin distribution
        for (size_t i = 0; i < all_tasks.size(); ++i) {
            thread_queues[i % num_threads][write_idx].push_back(all_tasks[i]);
        }
        
        // Swap ping-pong buffers
        std::swap(read_buffer, write_buffer);
    }
};
```

#### WorkStealingDeque with Batch Operations

**Per-Thread Work Deques**: Each thread maintains a cache-line-aligned deque optimized for `uint64_t` tasks with batch operations:

```cpp
class WorkStealingDeque {
private:
    alignas(64) std::atomic<size_t> top{0};
    alignas(64) std::atomic<size_t> bottom{0};
    alignas(64) std::vector<uint64_t> buffer;
    
public:
    // Batch push for multiple tasks (avoids excessive individual pushes)
    void push_batch(const std::vector<uint64_t>& tasks) {
        size_t b = bottom.load(std::memory_order_relaxed);
        size_t new_bottom = b + tasks.size();
        
        // Ensure buffer capacity
        if (new_bottom >= buffer.size()) {
            buffer.resize(std::max(new_bottom * 2, buffer.size()));
        }
        
        // Copy tasks to buffer
        for (size_t i = 0; i < tasks.size(); ++i) {
            buffer[(b + i) % buffer.size()] = tasks[i];
        }
        
        bottom.store(new_bottom, std::memory_order_release);
    }
    
    // Single push for immediate scheduling
    void push_bottom(uint64_t task) {
        size_t b = bottom.load(std::memory_order_relaxed);
        if (b >= buffer.size()) {
            buffer.resize(std::max(b * 2, size_t(64)));
        }
        buffer[b % buffer.size()] = task;
        bottom.store(b + 1, std::memory_order_release);
    }
    
    // Local pop (LIFO for cache locality)
    uint64_t pop_bottom() {
        size_t b = bottom.load(std::memory_order_relaxed);
        if (b == 0) return 0;  // Empty (0 is invalid task)
        
        b = b - 1;
        bottom.store(b, std::memory_order_relaxed);
        
        uint64_t task = buffer[b % buffer.size()];
        
        size_t t = top.load(std::memory_order_acquire);
        if (t <= b) {
            return task;  // Common case: no contention
        }
        
        // Contention with steal
        bottom.store(b + 1, std::memory_order_relaxed);
        return 0;
    }
    
    // Steal approximately half the current work
    std::vector<uint64_t> steal_half() {
        size_t t = top.load(std::memory_order_acquire);
        size_t b = bottom.load(std::memory_order_acquire);
        
        if (t >= b) return {};  // Empty
        
        size_t available = b - t;
        size_t steal_count = available / 2;
        if (steal_count == 0) steal_count = 1;
        
        // Try to reserve steal_count items
        if (!top.compare_exchange_weak(t, t + steal_count,
                                       std::memory_order_acq_rel,
                                       std::memory_order_relaxed)) {
            return {};  // Race with another stealer
        }
        
        // Extract stolen tasks
        std::vector<uint64_t> stolen;
        stolen.reserve(steal_count);
        for (size_t i = 0; i < steal_count; ++i) {
            stolen.push_back(buffer[(t + i) % buffer.size()]);
        }
        
        return stolen;
    }
};
```

#### Task Encoding as uint64_t

Tasks are encoded as `uint64_t` using a union structure with `uint8_t` tag, `uint8_t` ID field, and `uint24_t` object identifiers:

```cpp
union Task {
    uint64_t raw;
    uint32_t uint32s[2];
    uint8_t uint8s[8];
    
    static_assert(std::endian::native == std::endian::little, 
                  "Task encoding requires little-endian architecture");
    
    Task(uint8_t t, uint8_t i, uint32_t o1, uint32_t o2 = 0) {
        uint32s[0] = o1;
        uint32s[1] = o2;
        uint8s[0] = t;
        uint8s[4] = i;
    }
        
    // Fast accessors using array indexing (no shifts!)
    uint8_t get_type() const { return uint8s[0]; }
    uint8_t get_id() const { return uint8s[4]; }
    uint32_t get_ob1() const { return uint32s[0] & 0xFFFFFF; }
    uint32_t get_ob2() const { return uint32s[1] & 0xFFFFFF; }
};

enum TaskType : uint8_t {
    _UNUSED,                  // 0 = empty/invalid task
    MERGE_TASK,               // fields: {type, _, merged_ob, target_ob}
    EXISTS_TASK,              // fields: {type, _, new_ob, _}
    POSITIVE_ORDER_TASK,      // fields: {type, _, lhs_ob, rhs_ob}
    NEGATIVE_ORDER_TASK,      // fields: {type, _, lhs_ob, rhs_ob}
    UNARY_RELATION_TASK,      // fields: {type, relation_id, ob, _}
    BINARY_RELATION_TASK,     // fields: {type, relation_id, lhs_ob, rhs_ob}
    BINARY_FUNCTION_TASK,     // fields: {type, function_id, lhs_ob, rhs_ob}
    SYMMETRIC_FUNCTION_TASK,  // fields: {type, function_id, lhs_ob, rhs_ob}
    CLEANUP_TASK,             // fields: {type, cleanup_type, block_id, _}
    SAMPLE_TASK,              // fields: {type, _, target_size, _}
    ASSUME_TASK,              // fields: {type, _, theory_index, _}
    NLESS_BATCH_TASK          // fields: {type, _, start_ob, end_ob}
};
```

This encoding supports both surveyor (16-bit objects) and cartographer (24-bit objects, up to 16M) while fitting perfectly in 64 bits. The `id` field efficiently encodes relation/function identifiers, and the tag-based dispatch enables fast task type identification.

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

## Work Plan

The following tasks implement the scheduler redesign in incremental commits:

- [ ] Implement `WorkStealingDeque` class with cache-aligned atomics and LIFO/FIFO operations
- [ ] Add `ThreadBarrier` class using futex-based synchronization for BSP-style phase coordination  
- [ ] Create `HybridScheduler` class with double-buffered per-thread deques and ping-pong buffer management
- [ ] Replace current task queue system in `/pomagma/atlas/micro/scheduler.cpp` with hybrid scheduler interface
- [ ] Add task classification logic to route tasks to appropriate phases (merge/enforce/cleanup/batch)
- [ ] Implement phase transition logic with barrier synchronization and buffer swapping
- [ ] Add work stealing algorithm with NUMA-aware victim selection and batch stealing optimization
- [ ] Update database operations to use relaxed memory ordering while maintaining correctness through barriers
- [ ] Add saturation tracking to skip cleanup phase when no new inference is generated
- [ ] Update compiler to generate `IF_GLOBAL` guards for cleanup rules implemented in cartographer
