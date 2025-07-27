# Design Doc: Theorem Queues for Phased Inference

## Objective

Safely parallelize inference programs without resorting to atomic operations for large data structures by separating inference into a read-only proving phase followed by a write phase, connected by theorem queues.

## Background

### VM Execution in vm_impl.hpp

The virtual machine in `/pomagma/atlas/vm_impl.hpp` executes inference programs through opcodes that currently write directly to database structures. Critical write opcodes include:

- `INFER_EQUAL`: Calls `carrier().ensure_equal(lhs, rhs)` to merge equivalence classes
- `INFER_UNARY_RELATION`: Calls `rel.insert(key)` for unary predicates  
- `INFER_BINARY_RELATION`: Calls `rel.insert(lhs, rhs)` for binary relations
- `INFER_BINARY_FUNCTION`: Calls `fun.insert(lhs, rhs, val)` for function definitions

A typical instruction handling block demonstrates the current direct-write approach:

```cpp
case INFER_BINARY_RELATION: {
    BinaryRelation &rel = pop_binary_relation(program);
    Ob &lhs = pop_ob(program, context);
    Ob &rhs = pop_ob(program, context);
    rel.insert(lhs, rhs);  // Direct write to shared data structure
} break;
```

These direct writes occur during the proving phase within nested loops and conditional logic, creating contention on shared data structures. The VM processes millions of inference operations per second, with line 4837 in profiling data showing 17.9M calls consuming 59% of execution time.

### Surveyor Batch Inference in surveyor/infer.cpp

The surveyor's `infer_nless()` function implements parallel batch inference for NLESS monotonicity rules. It uses OpenMP parallelization with direct database writes:

```cpp
#pragma omp parallel
{
    for (Ob x = 1; x <= item_dim; ++x) {
        for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
            if (infer_nless_monotone(...)) {
                NLESS.insert(x, y);  // Direct write during proving
                schedule(NegativeOrderTask(x, y));
            }
        }
    }
}
```

This approach requires atomic operations on the `NLESS` relation and creates scheduling overhead during the proving phase.

### Cartographer Queue Architecture in cartographer/infer.cpp

The cartographer implements theorem queues with built-in lazy operations directly in the function classes:

- `BinaryFunction` and `SymmetricFunction` classes now have integrated `Queue` nested classes
- Thread-local worker queues collect theorems using `lazy_insert()` and `lazy_equate()` methods
- `lazy_gather()` merges worker queues into the main queue with mutex protection
- `lazy_flush()` applies all queued theorems atomically and returns the count

This pattern demonstrates the efficiency of collecting theorems during parallel proving phases and applying them atomically during synchronized write phases.

### Scheduler Coordination in scheduler.cpp

The current scheduler in `/pomagma/atlas/micro/scheduler.cpp` manages task queues with strict priority ordering:

1. **MergeTask** (exclusive, highest priority) - Equivalence class merging
2. **Enforce Tasks** (high priority) - Event-driven inference from GIVEN programs  
3. **AssumeTask** (initialization) - Loading facts from theory files
4. **SampleTask** (background) - Random object generation
5. **CleanupTask** (background) - Cleanup programs

The scheduler coordinates between incremental inference phases and batch inference phases using `vm::VirtualMachine::set_nless_monotone()` as a threshold mechanism.

## Design Overview

The design splits inference into two distinct phases connected by theorem queues:

1. **Proving Phase**: Read-only execution of inference programs that append discovered facts to thread-local theorem queues without modifying shared database structures.

2. **Write Phase**: Atomic application of queued theorems to database structures with proper synchronization and scheduling of follow-up tasks.

**BSP (Bulk Synchronous Parallel) Workflow**: Each inference cycle follows a barrier-synchronized pattern where all workers complete the proving phase before any worker begins the write phase. This eliminates race conditions and removes the need for atomic operations on large data structures during proving. *This implements the phased/BSP workflow described in [scheduler_design.md](scheduler_design.md) for reducing cleanup overhead.*

**Integrated Queue Architecture**: Instead of separate theorem queue classes, the design integrates lazy queueing directly into the function and relation classes themselves, using thread-local worker queues that merge into a main queue with mutex protection.

## Design Details

### Implementing Integrated Lazy Queues

**Performance Considerations**: Lazy queue operations must minimize overhead during the proving phase while supporting efficient batch application during the write phase. Based on cartographer profiling, queue operations should target sub-microsecond latency for individual insertions.

**Thread-Local Worker Queues**: Each function/relation maintains thread-local worker queues during the proving phase to avoid contention. The design uses static thread_local storage for efficient access:

```cpp
class BinaryFunction {
    struct Queue {
        std::vector<std::tuple<Ob, Ob, Ob>> m_tasks;
        void insert(Ob lhs, Ob rhs, Ob val);
        void clear();
    };
    
    Queue& worker_queue() const;
    mutable Queue m_queue;
    mutable std::mutex m_queue_mutex;
    static thread_local std::unordered_map<const BinaryFunction*, Queue>* s_worker_queues;
    
public:
    void lazy_insert(Ob lhs, Ob rhs, Ob val) const;
    void lazy_equate(Ob lhs1, Ob rhs1, Ob lhs2, Ob rhs2) const;
    void lazy_gather() const;   // called by worker threads
    size_t lazy_flush() const;  // called by main thread
};
```

**Automatic Deduplication**: The lazy queues use `sort_uniq()` and `union_sort_uniq()` utilities to deduplicate theorems before applying them to the database structures.

**Efficient Batch Application**: The `lazy_flush()` method applies all queued theorems in a single batch operation, providing better cache locality than individual insertions.

### Implementation in cartographer/infer.cpp

**Direct Integration**: The cartographer now uses the integrated lazy queue methods directly on function classes, eliminating the need for separate theorem queue classes.

**Preserved Optimization Patterns**: The core optimization patterns are maintained - thread-local collection during proving phases and mutex-protected merging during write phases.

**Proven Performance**: The implementation achieves linear scaling across CPU cores by avoiding contention during the proving phase and batching all database updates during the write phase.

### Refactoring surveyor/infer.cpp

**Adopting Cartographer Patterns**: The surveyor's `infer_nless()` function will be refactored to use the same theorem queue patterns as the cartographer:

```cpp
size_t infer_nless() {
    // ... setup code ...
#pragma omp parallel
    {
        // Proving phase - no direct writes
        for (Ob x = 1; x <= item_dim; ++x) {
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                if (infer_nless_monotone(...)) {
                    NLESS.lazy_insert(x, y);  // Queue instead of direct write
                }
            }
        }
        NLESS.lazy_gather();  // Merge worker queue to main queue
    }
    // Write phase - apply all queued theorems
    size_t theorem_count = NLESS.lazy_flush();
    return theorem_count;
}
```

**Integration with Task Scheduling**: The refactored surveyor will continue scheduling `NegativeOrderTask`s during the write phase, but task creation will be batched to reduce scheduling overhead.

### Implementation in vm_impl.hpp and scheduler.cpp

**VM Program Modification**: The core change involves replacing direct write opcodes with lazy queue operations:

```diff
case INFER_BINARY_RELATION: {
    BinaryRelation &rel = pop_binary_relation(program);
    Ob &lhs = pop_ob(program, context);
    Ob &rhs = pop_ob(program, context);
-   rel.insert(lhs, rhs);
+   rel.lazy_insert(lhs, rhs);
} break;
```

**Scheduler Phase Coordination**: The scheduler implements BSP-style coordination using OpenMP's implicit barriers:

```cpp
namespace Scheduler {
void execute_phased_vm_programs() {
    // Proving phase - programs distributed across threads
#pragma omp parallel
    {
        Context* context = vm.new_context();  // Gets thread-local context
        
#pragma omp for
        for (size_t i = 0; i < pending_programs.size(); ++i) {
            vm.execute(pending_programs[i], context);
        }
        // Each thread gathers its worker queues before barrier
        signature.gather_all_lazy_queues();
    }
    // Implicit OpenMP barrier here when parallel section ends
    
    // Write phase - main thread only
    signature.flush_all_lazy_queues();
}
}
```

### Analyst Integration and Single-Threaded Optimization

**Unified Interface**: The analyst's query execution uses VM programs for constraint solving and validation, so it naturally adopts the lazy queue interface without requiring separate code paths.

**Queue-Based Execution**: All execution modes, including single-threaded analyst queries, use the unified lazy queue approach. For single-threaded scenarios, the queue overhead is minimal since there's no contention, and the batch application provides better cache locality.

**Performance Characteristics**: Single-threaded analyst queries experience minimal overhead from lazy queueing since queue operations are simple vector pushes. The batch application during the write phase often improves cache performance compared to scattered individual insertions.

**Session Management**: The analyst server adopts the same phased execution pattern as the surveyor, with a proving phase that collects theorems followed by a write phase that applies them atomically.

### OpenMP Barrier Coordination

**Implicit Synchronization**: OpenMP provides automatic barriers at the end of parallel sections, eliminating the need for custom barrier implementations. The proving phase completes when all threads finish their work, and the write phase executes sequentially on the main thread.

**Thread-Safe Merging**: The `merge_from_thread()` method uses a simple mutex to protect the global theorem queues during the merge operation at the end of the proving phase. Since this happens only once per thread, the synchronization overhead is minimal.

**Deadlock Prevention**: By using OpenMP's built-in barrier mechanism, the design maintains compatibility with the scheduler's existing task priority system. Merge tasks continue to be handled outside the phased execution workflow.

### Memory Management and Performance

**Queue Memory Allocation**: Lazy queues use efficient vector-based storage with capacity management - queues that grow beyond 1024 entries are reallocated to prevent memory bloat.

**Cache Optimization**: The proving phase maintains cache locality by processing VM programs in work-stealing order, while the write phase applies theorems in database-friendly order through the batched flush operations.

**Thread-Local Storage**: The design uses static thread_local maps to efficiently access worker queues without contention or lookup overhead.

## Work Plan

- [x] Implement integrated lazy queue architecture directly in `BinaryFunction` and `SymmetricFunction` classes
- [x] Add thread-local worker queues with `lazy_insert()`, `lazy_equate()`, `lazy_gather()`, and `lazy_flush()` methods
- [x] Update cartographer/infer.cpp to use lazy queue methods instead of separate theorem queue classes
- [x] Replace `BinaryFunctionTheoremQueue` with direct lazy operations in atlas functions
- [ ] Modify VM opcodes `INFER_*` in vm_impl.hpp to use lazy queue methods instead of direct insertion
- [ ] Add phased execution methods to scheduler.cpp using OpenMP implicit barriers between proving and write phases
- [ ] Refactor surveyor/infer.cpp to use lazy queue infrastructure instead of direct `NLESS.insert()` calls during parallel computation
- [ ] Update all VM callers (surveyor, analyst) to use lazy queue execution patterns
- [ ] Add performance benchmarks comparing lazy queue vs direct execution throughput and latency
- [ ] Update scheduler task priority handling to batch task creation during write phase instead of individual scheduling during proving
- [x] Add cross-references and links between this document and scheduler_design.md for the broader BSP scheduling context
- [ ] Test integration with existing cleanup task system to ensure phased inference doesn't interfere with cleanup program execution
- [ ] Validate memory usage patterns and cache behavior under high-concurrency lazy queue workloads
- [ ] Document migration guide for other components that may need to adopt lazy queue patterns in the future 