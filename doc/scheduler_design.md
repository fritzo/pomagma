# Design Doc: Cartographer Scheduler Implementation

## Objective

Implement complete forward-chaining inference capabilities in the cartographer by incorporating the surveyor's scheduler patterns, phased execution, and cleanup reduction optimizations. This eliminates the need for separate surveyor and cartographer inference engines.

## Background

### Architecture Overview

**NEW DIRECTION:** Pomagma will consolidate into a single **enhanced cartographer** that combines forward-chaining database construction with scalable batch operations. The enhanced cartographer will operate on **16-bit identifiers** (up to 65K E-classes) using macro atlases, enhanced with complete inference capabilities through a new scheduler implementation based on proven surveyor patterns.

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

### Enhanced Cartographer: Unified Growth and Inference Model

**NEW DIRECTION:** The enhanced cartographer will unify the surveyor's complete inference capabilities with the cartographer's scalable batch operations. Rather than maintaining separate engines, the enhanced cartographer will support:

1. **Complete forward-chaining inference** through a new scheduler implementation (this document)
2. **Database growth** through sampling and saturation via a new `.survey()` method  
3. **Batch operations** for truncation, merging, and aggregation

The **enhanced cartographer will grow, truncate, and merge** databases while maintaining complete inference capabilities. It implements the following operations:

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

1. **Reduce cleanup work** by refactoring the surveyor incremental scheduler to use acquire-release semantics and a phased/BSP (Bulk Synchronous Parallel) workflow. This eliminates the need for a final cleanup phase by ensuring incremental inference is complete. *See [inference_queues.md](inference_queues.md) for the detailed implementation of phased inference using theorem queues.*

2. **Avoid initial cleanup work** for rules implemented in the cartographer by detecting when databases have already been processed by the cartographer's rule set.
This requires the compiler to add `IF_GLOBAL` guards to cleanup rules that are known to be implemented in the cartographer.

3. **Track saturation status** and avoid initial cleanup phase if a database is already saturated (e.g. if it is not the result of a merger). Since saturation depends on the ruleset, we need to track rule sets. The main source of non-saturation is when the cartographer merges databases then only partially saturates them with respect to its incomplete rule set.

## Design Details

### Surveyor scheduler redesign

The redesigned scheduler addresses the fundamental completeness issues by implementing **BSP-style partial total ordering** with relaxed atomics and **simple dynamic work distribution** for performance. The key insight is that we need strict ordering between phases for correctness, but within each phase, task execution order doesn't matter, eliminating the need for FIFO queues.

#### Core Design Principles

**BSP-style Partial Total Ordering**: The scheduler enforces that all tasks in phase N complete before any task in phase N+1 begins, ensuring completeness without requiring global sequential ordering within phases.

**Relaxed Memory Ordering with Barriers**: With full barriers between phases, database operations can use `std::memory_order_relaxed` for performance, since the barriers provide necessary synchronization points. Only the barriers themselves need acquire-release semantics.

**Simple Dynamic Work Distribution**: Use a single shared `std::atomic_size_t` counter for work distribution, similar to OpenMP's `schedule(dynamic,1)` approach, eliminating the complexity of work-stealing algorithms.

#### Phased Scheduler Architecture

The scheduler uses atomic work distribution where the main thread first computes the total work across all functions and relations, then creates a shared counter for work distribution:

```cpp
class PhasedScheduler {
private:
    std::atomic<size_t> next_task{0};
    std::vector<TaskRef> task_refs;
    ThreadBarrier phase_barrier;

public:
    void execute_inference_phase() {
        // Main thread: compute total work and build task table
        build_task_table();
        next_task.store(0, std::memory_order_relaxed);
        
        // All threads: process tasks using atomic work distribution
        #pragma omp parallel
        {
            size_t task_id;
            while ((task_id = next_task.fetch_add(1, std::memory_order_relaxed)) < task_refs.size()) {
                const TaskRef& ref = task_refs[task_id];
                process_task(ref);
            }
        }
        // Implicit OpenMP barrier here
        
        // Main thread: apply all queued facts
        flush_all_queues();
    }
    
private:
    void build_task_table() {
        task_refs.clear();
        
        // Iterate over functions and relations to compute total work
        for (auto* binary_func : signature.binary_functions()) {
            size_t antecedent_count = binary_func->antecedent_count();
            if (antecedent_count > 0) {
                task_refs.push_back({binary_func, 0, antecedent_count});
            }
        }
        
        for (auto* binary_rel : signature.binary_relations()) {
            binary_rel->build_index();  // Prepare tile index for NLESS/LESS
            size_t tile_count = binary_rel->task_count();
            for (size_t i = 0; i < tile_count; ++i) {
                task_refs.push_back({binary_rel, i, 1});  // 1 tile per task
            }
        }
    }
};
```

#### Global Task Index with OpenMP Dynamic Scheduling

The distributed queue architecture uses OpenMP's proven `schedule(dynamic,1)` work distribution with a global task index that maps to symbol-specific work chunks. This eliminates the need for custom work-stealing implementations while providing excellent load balancing.

**Performance Target**: Each task should take >100ns-1μs to keep scheduling overhead <1% (atomic fetch_add costs ~1-10ns).

**Task Granularity Strategy**:
```cpp
// NLESS/LESS: hierarchical queues naturally provide 256×256 tile granularity
// Each (ObHigh, ObHigh) key in BinaryRelation::Queue represents a tile
struct NLESSTileProcessing {
    // No explicit tile encoding needed - use hierarchical queue structure directly
    // Each queue.get_task(i) returns (HighPair, LowQueue&) for tile processing
    // Each tile: up to 65K NLESS operations = optimal parallel granularity
    
    static void process_tile(const BinaryRelation::Queue::HighPair& hi_pair,
                           const BinaryRelation::Queue::LowQueue& lo_queue) {
        auto [i_hi, j_hi] = hi_pair;
        for (auto [i_lo, j_lo] : lo_queue) {
            Ob i = ob_from_hi_lo(i_hi, i_lo);
            Ob j = ob_from_hi_lo(j_hi, j_lo);
            // Process NLESS fact (i, j)
        }
    }
};

// Other heavy symbols: chunk to hit ~1-10μs per task  
struct APPChunkSize { static constexpr size_t value = 1024; };   // ~1024 APP ops = ~2μs

// Light symbols: process individually
struct EQUALChunkSize { static constexpr size_t value = 1; };    // Each EQUAL op = ~50ns
```

**Global Task Scheduler Implementation**:
```cpp
struct TaskRef {
    Symbol* symbol;
    size_t start_index;
    size_t count;
};

class GlobalTaskScheduler {
    std::vector<TaskRef> task_refs;
    std::atomic<size_t> global_task_index{0};
    
public:
    void build_task_table() {
        task_refs.clear();
        
        // Add tile tasks for NLESS/LESS - use hierarchical queue structure
        for (auto* nless : signature.binary_relations_of_type<NLESS>()) {
            nless->build_index();  // Prepare tile index
            size_t tile_count = nless->m_consequents.task_count();
            
            for (size_t i = 0; i < tile_count; ++i) {
                task_refs.push_back({nless, i, 1});  // 1 tile per task
            }
        }
        
        // Add individual tasks for light symbols
        for (auto* equal : signature.binary_relations_of_type<EQUAL>()) {
            size_t total = equal->antecedent_count();
            for (size_t i = 0; i < total; ++i) {
                task_refs.push_back({equal, i, 1});
            }
        }
    }
    
    void execute_parallel() {
        size_t total_tasks = task_refs.size();
        
        #pragma omp parallel
        {
            size_t task_id;
            while ((task_id = global_task_index.fetch_add(1)) < total_tasks) {
                const TaskRef& ref = task_refs[task_id];
                // For tile-based relations (NLESS/LESS): process entire tile
                // For other relations: process individual chunks
                ref.symbol->process_antecedent_task(ref.start_index, ref.count);
            }
        }
    }
};
```

**Benefits**:
- **Proven scheduler**: OpenMP's `dynamic(1)` handles load balancing automatically
- **Minimal overhead**: Single atomic fetch_add per task with <1% scheduling cost
- **Tunable granularity**: Chunk sizes optimized per symbol type based on operation cost
- **Simple implementation**: No custom work stealing logic required
- **NLESS-aware**: Heavy operations like NLESS are chunked for efficient parallel processing

#### Distributed Queue Architecture

**OBSOLETE**: This section described task encoding for global task queues, but the new design distributes tasks into per-symbol antecedent and consequent queues within each function/relation class. Tasks are no longer encoded as `uint64_t` values but stored directly as fact tuples (e.g., `std::tuple<Ob, Ob, Ob>` for binary functions) in the appropriate symbol's queue.

The distributed approach eliminates the need for task type encoding and dispatch since each queue is typed to its specific function/relation and contains facts ready for direct processing.

#### Performance Optimizations

**Atomic Work Distribution**: Single `fetch_add(1)` operation per task provides excellent load balancing with minimal overhead (~1-10ns per task).

**Task Granularity Tuning**: Each task is sized to take >100ns-1μs to keep scheduling overhead <1% of total execution time.

#### Implementation Strategy

1. **Use atomic work counters** for simple, efficient work distribution
2. **Add phase barriers** using OpenMP's implicit synchronization for BSP-style completion guarantees  
3. **Keep relaxed memory ordering** since barriers provide synchronization
4. **Build task tables** by iterating over functions and relations to compute total work
5. **Optimize for common case** where cleanup phase becomes empty

The atomic counter approach provides:
- **Clean phase separation** through OpenMP barriers (eliminates race conditions)
- **Excellent load balancing** through dynamic work distribution with minimal overhead
- **Simple implementation** without complex work-stealing or queue management
- **Performance** through relaxed atomics with barrier synchronization

### Expression Queue Architecture for Enhanced Cartographer

**Consequent Queues as RETE Agenda**: The enhanced cartographer will implement consequent queues that function as a RETE-style agenda or conflict set - newly inserted facts waiting to trigger `GIVEN_*` program execution. Each function and relation class maintains both antecedent queues (facts to insert) and consequent queues (facts that trigger programs):

1. **DB Write Phase**: When antecedent facts are inserted during `lazy_flush()`, newly inserted facts populate consequent queues
2. **Program Activation**: Facts in consequent queues trigger execution of corresponding `GIVEN_*` programs compiled from inference rules  
3. **Queue Processing**: Programs execute in read-only mode, adding new facts to antecedent queues for the next cycle

**Batch Queue Merge Processing**: Both antecedent and consequent queues must be updated after `process_mergers()` completes to replace deprecated object references with canonical representatives. Each `Queue` class implements efficient batch processing via `process_mergers()` methods that perform in-place compaction for unchanged tasks and separate collection for tasks requiring deduplication:

```cpp
void update_all_queues_after_mergers() {
    // Batch-update all component queues after merging completes
#define POMAGMA_UPDATE_QUEUES(arity)                    \
    for (auto i : m_structure.signature().arity()) {    \
        i.second->m_consequents.process_mergers(        \
            *m_structure.signature().carrier());         \
        /* Future: i.second->m_antecedents.process_mergers() */ \
    }

    POMAGMA_UPDATE_QUEUES(binary_functions);
    POMAGMA_UPDATE_QUEUES(symmetric_functions);
    POMAGMA_UPDATE_QUEUES(injective_functions);
    POMAGMA_UPDATE_QUEUES(nullary_functions);
    POMAGMA_UPDATE_QUEUES(unary_relations);
    POMAGMA_UPDATE_QUEUES(binary_relations);

#undef POMAGMA_UPDATE_QUEUES
}
```

**Efficiency Benefits of Batch Queue Processing**:
- **In-place compaction** for unchanged tasks minimizes memory allocation  
- **Separate collection** only for changed tasks reduces sorting overhead
- **Single deduplication** after all merges complete eliminates redundant work
- **No per-merge locking** eliminates contention during merge processing
- **Coordinated with existing infrastructure** using the established `process_mergers()` workflow

**Checkpointed Inference with Persistent Queues**: For low-latency checkpointing (crucial for AWS EC2 spot instances), both antecedent and consequent queues should support persistence alongside database state. This enables:

- **Frequent checkpointing** without losing in-flight inference work
- **Fast restart** from checkpoints with queued work intact  
- **Incremental state saving** where only queue deltas need persistence

The antecedent and consequent queues become part of the persistent database state, allowing inference to checkpoint mid-cycle and resume exactly where it left off.

### Critical Design Issues for Queue Processing

**Merge Saturation Requirements**: The scheduler must coordinate queue processing with object merging to maintain correctness. Two critical issues arise:

**Issue 1 - Iterative Saturation**: Antecedent queue population during flush operations may trigger additional object mergers, requiring the scheduler to loop until saturation:

```cpp
class CartographerScheduler {
public:
    size_t execute_inference_cycle() {
        size_t total_work = 0;
        do {
            // Process carrier merges first (highest priority)
            total_work += process_carrier_antecedents();
            
            // Process function/relation antecedents, which may trigger more carrier merges
            total_work += process_component_antecedents();
            
            // Process object mergers and batch-update all queues
            process_mergers(m_structure.signature());
            
            // Update all component queues after merging completes
            update_all_queues_after_mergers();
            
        } while (has_pending_carrier_antecedents());
        
        return total_work;
    }
};
```

**Issue 2 - Antecedent Semantics for GIVEN Program Triggering**: The scheduler must process antecedents for both genuine insertions and value merges. When existing values merge (e.g., `val1` and `val2` become `rep`), the resulting canonical fact `(lhs, rhs, rep)` must trigger GIVEN programs because it represents new logical information. This requires:

1. **Modified insert semantics**: Atlas `insert()` methods return `true` for both new entries and value merges
2. **Complete antecedent capture**: All logically significant changes populate antecedent queues
3. **Merge-aware scheduling**: The scheduler processes merged facts as new work items

This ensures that GIVEN program execution achieves logical completeness by firing on all canonical facts, not just initial insertions.

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

The following tasks implement the cartographer scheduler in incremental commits:

- [ ] Create `pomagma/cartographer/scheduler.hpp` and `scheduler.cpp` based on proven surveyor patterns
- [ ] Implement scheduler that processes distributed antecedent/consequent queues in each atlas component
- [ ] Add `ThreadBarrier` class using futex-based synchronization for BSP-style phase coordination  
- [ ] Create phased execution logic that coordinates antecedent flushing and consequent processing across all atlas components
- [ ] Implement phase transition logic with barrier synchronization for coordinated queue processing
- [ ] Integrate with cartographer's macro atlas operations using relaxed memory ordering with barriers
- [ ] Add saturation tracking to skip cleanup phase when no new inference is generated
- [ ] Extend atlas function/relation classes with antecedent and consequent queue pairs for RETE-style agenda functionality
- [ ] Implement `process_consequents()` methods in each class to trigger corresponding GIVEN_* programs
- [ ] Extend `process_mergers()` to call `update_antecedent_values()` and `update_consequent_values()` during object merging
- [ ] Add persistence support for both antecedent and consequent queues to enable frequent checkpointing and fast restart
- [ ] Update compiler to generate complete rule sets optimized for macro atlas (no inverse table dependencies)
