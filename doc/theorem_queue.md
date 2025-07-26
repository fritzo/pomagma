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

The cartographer already implements theorem queues with three distinct classes:

- `TheoremQueue`: General-purpose queue for `(Ob, Ob)` pairs with `try_push()` for conditional insertion and `flush()` with mutex protection
- `LhsFixedTheoremQueue`: Optimized for relations with fixed left-hand side using `DenseSet` for efficient batch insertion
- `BinaryTheoremQueue`: Handles function equality constraints using `std::unordered_set` for deduplication

The cartographer's pattern demonstrates the efficiency of collecting theorems during parallel proving phases and applying them atomically during synchronized write phases.

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

**Theorem Queue Abstraction**: A unified queue interface supports different optimization patterns (per-thread collection, batched insertion, deduplication) while maintaining compatibility with existing cartographer queue implementations.

## Design Details

### Implementing Efficient Theorem Queues

**Performance Considerations**: Theorem queues must minimize overhead during the proving phase while supporting efficient batch application during the write phase. Based on cartographer profiling, queue operations should target sub-microsecond latency for individual insertions.

**Per-Thread Queues with Global Merging**: Each worker thread maintains private theorem queues during the proving phase to avoid contention. During the write phase, a designated coordinator thread merges all per-thread queues before applying theorems:

```cpp
class TheoremQueue {
    std::vector<UnaryTheoremQueue> unary_queues;
    std::vector<BinaryTheoremQueue> binary_queues;
    std::vector<FunctionTheoremQueue> function_queues;
    std::mutex merge_mutex;  // Protects merging from multiple threads
    
public:
    void prove_phase_push_unary(uint8_t rel_id, Ob arg);
    void prove_phase_push_binary(uint8_t rel_id, Ob lhs, Ob rhs);
    void prove_phase_push_function(uint8_t fun_id, Ob lhs, Ob rhs, Ob val);
    
    void merge_from_thread(const TheoremQueue& local_queues);
    void write_phase_apply_all(Signature& signature);
};
```

**Compression and Deduplication**: Relations and functions are referenced by 8-bit indices matching the VM's addressing scheme. Binary relation queues use `std::unordered_set<std::pair<Ob, Ob>>` for automatic deduplication. Function queues deduplicate on `(lhs, rhs)` keys, resolving value conflicts through the equivalence system.

**Batched Insertion APIs**: Theorem queues provide batched insertion methods that leverage existing optimized bulk operations in the atlas data structures:

```cpp
void BinaryRelationQueue::flush_to(BinaryRelation& rel) {
    if (m_lhs_fixed && m_pairs.size() > BATCH_THRESHOLD) {
        // Use DenseSet bulk insertion like cartographer
        DenseSet rhs_set(rel.item_dim());
        for (const auto& pair : m_pairs) {
            rhs_set.insert(pair.second);
        }
        rel.insert(m_lhs, rhs_set);
    } else {
        // Individual insertions for mixed patterns
        for (const auto& pair : m_pairs) {
            rel.insert(pair.first, pair.second);
        }
    }
}
```

### Refactoring cartographer/infer.cpp

**Factoring Out Existing Queues**: The cartographer's theorem queue implementations will be moved to a shared location (`/pomagma/atlas/theorem_queue.hpp`) for reuse by other components. The interface will be generalized to support different atlas types (micro vs macro) through template parameters.

**Preserving Optimization Patterns**: Critical optimizations like `LhsFixedTheoremQueue` will be retained and extended. The pattern detection logic that chooses between general and specialized queue types will be made available to the VM system.

**Maintaining Performance**: Existing cartographer benchmark results show the queue approach achieves linear scaling across CPU cores. The refactoring will preserve these characteristics by maintaining the same mutex granularity and batching strategies.

### Refactoring surveyor/infer.cpp

**Adopting Cartographer Patterns**: The surveyor's `infer_nless()` function will be refactored to use the same theorem queue patterns as the cartographer:

```cpp
size_t infer_nless() {
    // ... setup code ...
    std::mutex mutex;
#pragma omp parallel
    {
        LhsFixedTheoremQueue theorems(NLESS);
        // Proving phase - no direct writes
        for (Ob x = 1; x <= item_dim; ++x) {
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                if (infer_nless_monotone(...)) {
                    theorems.push(x, y);  // Queue instead of direct write
                }
            }
            theorems.flush(mutex);  // Write phase
        }
    }
}
```

**Integration with Task Scheduling**: The refactored surveyor will continue scheduling `NegativeOrderTask`s during the write phase, but task creation will be batched to reduce scheduling overhead.

### Adding Write Phase to vm_impl.hpp and scheduler.cpp

**VM Program Modification**: The core change involves replacing direct write opcodes with a unified inference interface. Since Context is already thread-local, it can directly own the theorem queues:

```cpp
struct Context {
    // ... existing fields ...
    TheoremQueue theorem_queues;
    
    void clear() {
        // ... existing clear logic ...
        theorem_queues.clear();  // Reset queues for reuse
    }
};

// Helper function that always uses queues
template<typename Relation>
void infer(Context* context, Relation& rel, Ob lhs, Ob rhs) {
    context->theorem_queues.prove_phase_push_binary(rel.id(), lhs, rhs);
}
```

The instruction handling transformation eliminates direct database writes by routing all inference through a unified interface:

```diff
case INFER_BINARY_RELATION: {
    BinaryRelation &rel = pop_binary_relation(program);
    Ob &lhs = pop_ob(program, context);
    Ob &rhs = pop_ob(program, context);
-   rel.insert(lhs, rhs);
+   infer(context, rel, lhs, rhs);
} break;
```

**Scheduler Phase Coordination**: The scheduler will implement BSP-style coordination using OpenMP's implicit barriers:

```cpp
namespace Scheduler {
void execute_phased_vm_programs() {
    TheoremQueue global_queues;
    
    // Proving phase - programs distributed across threads
#pragma omp parallel
    {
        Context* context = vm.new_context();  // Gets thread-local context
        
#pragma omp for
        for (size_t i = 0; i < pending_programs.size(); ++i) {
            vm.execute(pending_programs[i], context);
        }
        // Each thread contributes to global queues before barrier
        global_queues.merge_from_thread(context->theorem_queues);
    }
    // Implicit OpenMP barrier here when parallel section ends
    
    // Write phase - main thread only
    global_queues.write_phase_apply_all(signature);
}
}
```

### Analyst Integration and Single-Threaded Optimization

**Unified Interface**: The analyst's query execution uses VM programs for constraint solving and validation, so it will naturally adopt the unified `infer()` interface without requiring separate code paths.

**Queue-Based Execution**: All execution modes, including single-threaded analyst queries, use the unified queue-based approach. For single-threaded scenarios, the queue overhead is minimal since there's no contention, and the batch application provides better cache locality.

**Performance Characteristics**: Single-threaded analyst queries experience minimal overhead from queueing since queue operations are simple vector pushes. The batch application during the write phase often improves cache performance compared to scattered individual insertions.

**Session Management**: The analyst server adopts the same phased execution pattern as the surveyor, with a proving phase that collects theorems followed by a write phase that applies them atomically.

### OpenMP Barrier Coordination

**Implicit Synchronization**: OpenMP provides automatic barriers at the end of parallel sections, eliminating the need for custom barrier implementations. The proving phase completes when all threads finish their work, and the write phase executes sequentially on the main thread.

**Thread-Safe Merging**: The `merge_from_thread()` method uses a simple mutex to protect the global theorem queues during the merge operation at the end of the proving phase. Since this happens only once per thread, the synchronization overhead is minimal.

**Deadlock Prevention**: By using OpenMP's built-in barrier mechanism, the design maintains compatibility with the scheduler's existing task priority system. Merge tasks continue to be handled outside the phased execution workflow.

### Memory Management and Performance

**Queue Memory Allocation**: Theorem queues will use arena allocation for efficient memory management during high-throughput proving phases. Thread-local arenas will be reset after each phase transition.

**Cache Optimization**: The proving phase will maintain cache locality by processing VM programs in work-stealing order, while the write phase will apply theorems in database-friendly order (sorted by target relation/function).

**Fallback Mechanisms**: For compatibility with existing code, the VM will support both phased and direct execution modes. Single-threaded analyst queries will continue using direct execution for minimal latency.

## Work Plan

- [x] Extract theorem queue classes from cartographer/infer.cpp into shared header `/pomagma/atlas/theorem_queue.hpp` with template support for micro/macro atlas types
- [ ] Implement `TheoremQueue` class with thread-safe merging and BSP-style coordination using OpenMP implicit barriers
- [ ] Add a `TheoremQueue` to the `Context` to capture queue theorems instead of direct database writing during proving phases
- [ ] Modify VM opcodes `INFER_*` in vm_impl.hpp to route through theorem queues when in proving context mode
- [ ] Add phased execution methods to scheduler.cpp using OpenMP implicit barriers between proving and write phases for VM program execution
- [ ] Refactor surveyor/infer.cpp to use shared theorem queue infrastructure instead of direct `NLESS.insert()` calls during parallel computation
- [ ] Update all VM callers (surveyor, analyst) to provide theorem queue contexts for unified phased execution
- [ ] Implement arena memory allocation for theorem queues to optimize allocation/deallocation patterns during high-throughput inference
- [ ] Add performance benchmarks comparing phased vs direct execution throughput and latency across different workload patterns
- [ ] Update scheduler task priority handling to batch task creation during write phase instead of individual scheduling during proving
- [x] Add cross-references and links between this document and scheduler_design.md for the broader BSP scheduling context
- [ ] Test integration with existing cleanup task system to ensure phased inference doesn't interfere with cleanup program execution
- [ ] Validate memory usage patterns and cache behavior under high-concurrency phased inference workloads
- [ ] Document migration guide for other components that may need to adopt phased inference patterns in the future 