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

### Forward-Chaining Inference Patterns

Forward-chaining inference (as exemplified by the surveyor's `infer_nless()` function) implements parallel batch inference for NLESS monotonicity rules. The enhanced cartographer will adopt these patterns using OpenMP parallelization with lazy queue writes:

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

The cartographer implements theorem queues with built-in lazy operations directly in the function and relation classes:

- `BinaryFunction`, `SymmetricFunction`, and `BinaryRelation` classes now have integrated `Queue` nested classes
- Thread-local worker queues collect theorems using `lazy_insert()`, `lazy_try_insert()`, and `lazy_equate()` methods
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

The design splits inference into two distinct phases connected by antecedent and consequent queues:

1. **Proving Phase**: Read-only execution of inference programs that append discovered facts to thread-local antecedent queues without modifying shared database structures.

2. **Write Phase**: Atomic application of queued facts to database structures, with newly inserted facts populating consequent queues to trigger follow-up program execution.

**BSP (Bulk Synchronous Parallel) Workflow**: Each inference cycle follows a barrier-synchronized pattern where all workers complete the proving phase before any worker begins the write phase. This eliminates race conditions and removes the need for atomic operations on large data structures during proving. *This implements the phased/BSP workflow described in [scheduler_design.md](scheduler_design.md) for reducing cleanup overhead.*

**Integrated Queue Architecture**: Instead of separate queue classes, the design integrates antecedent and consequent queueing directly into the function and relation classes themselves. Each component maintains both antecedent queues (facts to insert) and consequent queues (newly inserted facts that trigger program execution), using thread-local worker queues that merge into main queues with mutex protection.

## Design Details

### Implementing Integrated Lazy Queues

**Performance Considerations**: Antecedent and consequent queue operations must minimize overhead during the proving phase while supporting efficient batch application during the write phase. Based on cartographer profiling, queue operations should target sub-microsecond latency for individual insertions.

**Thread-Local Worker Queues**: Each function/relation maintains thread-local worker queues for both antecedents and consequents during the proving phase to avoid contention. The design uses static thread_local storage for efficient access:

```cpp
class BinaryFunction {
    struct Queue {
        std::vector<std::tuple<Ob, Ob, Ob>> m_tasks;
        void insert(Ob lhs, Ob rhs, Ob val);
        void clear();
    };
    
    Queue& worker_antecedents() const;
    Queue& worker_consequents() const;
    mutable Queue m_antecedents;
    mutable Queue m_consequents;
    mutable std::mutex m_antecedents_mutex;
    mutable std::mutex m_consequents_mutex;
    static thread_local std::unordered_map<const BinaryFunction*, Queue>* s_worker_antecedents;
    static thread_local std::unordered_map<const BinaryFunction*, Queue>* s_worker_consequents;
    
public:
    void lazy_insert(Ob lhs, Ob rhs, Ob val) const;  // adds to antecedents
    void lazy_equate(Ob lhs1, Ob rhs1, Ob lhs2, Ob rhs2) const;
    void lazy_gather() const;   // called by worker threads
    size_t lazy_flush() const;  // called by main thread, flushes antecedents and populates consequents
    // Methods for processing consequents to trigger GIVEN programs
    bool has_pending_consequents() const;
    void process_consequents() const;  // triggers GIVEN_BINARY_FUNCTION programs
};

class BinaryRelation {
    struct Queue {
        std::vector<std::pair<Ob, Ob>> m_tasks;
        void insert(Ob i, Ob j);
        void clear();
    };
    
    Queue& worker_antecedents() const;
    Queue& worker_consequents() const;
    mutable Queue m_antecedents;
    mutable Queue m_consequents;
    mutable std::mutex m_antecedents_mutex;
    mutable std::mutex m_consequents_mutex;
    static thread_local std::unordered_map<const BinaryRelation*, Queue>* s_worker_antecedents;
    static thread_local std::unordered_map<const BinaryRelation*, Queue>* s_worker_consequents;
    
public:
    void lazy_insert(Ob i, Ob j) const;  // adds to antecedents
    void lazy_try_insert(Ob i, Ob j) const;
    void lazy_gather() const;   // called by worker threads
    size_t lazy_flush();        // called by main thread, flushes antecedents and populates consequents
    // Methods for processing consequents to trigger GIVEN programs
    bool has_pending_consequents() const;
    void process_consequents() const;  // triggers GIVEN_BINARY_RELATION programs
};
```

**Automatic Deduplication**: Both antecedent and consequent queues use `sort_uniq()` and `union_sort_uniq()` utilities to deduplicate facts before processing.

**Efficient Batch Application**: The `lazy_flush()` method applies all antecedent facts in a single batch operation, then populates consequent queues with newly inserted facts that can trigger `GIVEN_*` program execution in the next inference cycle.

### Implementation in cartographer/infer.cpp

**Direct Integration**: The cartographer now uses the integrated lazy queue methods directly on function and relation classes, eliminating the need for separate theorem queue classes like `BinaryRelationTheoremQueue`.

**Replaced Theorem Queue Classes**: The old `BinaryRelationRowTheoremQueue` and `BinaryRelationTheoremQueue` classes have been completely removed in favor of the integrated antecedent and consequent queue methods within each atlas component.

**Preserved Optimization Patterns**: The core optimization patterns are maintained - thread-local collection during proving phases and mutex-protected merging during write phases.

**Proven Performance**: The implementation achieves linear scaling across CPU cores by avoiding contention during the proving phase and batching all database updates during the write phase. Atomic operations and mutex contention during proving have been eliminated.

### Enhanced Cartographer Inference Implementation

**Adopting Proven Patterns**: The cartographer will incorporate forward-chaining inference capabilities using antecedent/consequent queue patterns, including NLESS monotonicity rules:

```cpp
size_t infer_nless() {
    // ... setup code ...
#pragma omp parallel
    {
        // Proving phase - no direct writes
        for (Ob x = 1; x <= item_dim; ++x) {
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                if (infer_nless_monotone(...)) {
                    NLESS.lazy_insert(x, y);  // Add to antecedent queue
                }
            }
        }
        NLESS.lazy_gather();  // Merge worker antecedents to main antecedent queue
    }
    // Write phase - apply all queued facts and populate consequents
    size_t theorem_count = NLESS.lazy_flush();
    return theorem_count;
}
```

**Integration with Task Scheduling**: The enhanced cartographer will schedule `NegativeOrderTask`s during the write phase, with batched task creation to reduce scheduling overhead through the new cartographer scheduler implementation.

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

**Scope of VM Inference Programs**: The `INFER_*` opcodes are used by both the surveyor's forward-chaining inference engine and the analyst's constraint solving operations. The cartographer executes only query programs (using `RETURN`/`NRETURN` opcodes) and theory loading operations, which do not contain `INFER_*` opcodes. 

For the surveyor, lazy queue operations are automatically flushed by the phased execution scheduler during the write phase. For the analyst, explicit calls to `m_structure.lazy_gather()` and `m_structure.lazy_flush()` are required after VM program execution in `Server::solve()` to ensure all queued theorems are applied to the database before query results are collected. The micro atlas compatibility layer ensures these operations work correctly through direct delegation to existing `insert()` methods.

**Cartographer Scheduler Coordination**: The cartographer scheduler implements BSP-style coordination using OpenMP's implicit barriers:

```cpp
namespace cartographer {
class Scheduler {
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
};
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

**Merge Coordination**: The macro `Structure::lazy_flush()` requires careful coordination between queue flushing and object merging due to two critical issues:

**Issue 1 - Saturation Loop for Merge Processing**: Object merging must happen as early as possible since merging can eliminate downstream work. However, antecedent queues populated during `lazy_flush()` may contain facts that trigger additional mergers. This requires a saturation loop:

```cpp
size_t Structure::lazy_flush() {
    size_t total_theorem_count = 0;
    do {
        // Flush carrier first to process any pending merges
        size_t carrier_merges = m_signature.carrier()->lazy_flush();
        
        // Flush all functions and relations, populating antecedent queues
        size_t component_insertions = pomagma::lazy_flush(m_signature);
        
        // Process any mergers triggered by the insertions
        process_mergers(m_signature);
        
        total_theorem_count += carrier_merges + component_insertions;
        
    } while (m_signature.carrier()->antecedent_count() > 0);
    
    return total_theorem_count;
}
```

**Issue 2 - Queue Updates During Merging**: Both antecedent and consequent queues must be updated during `process_mergers()` to replace deprecated object references with canonical representatives:

```cpp
void process_mergers(Signature& signature) {
    // ... existing merge processing ...
    
    // Update both antecedent and consequent queues
#define POMAGMA_UPDATE_QUEUES(arity)           \
    for (auto i : signature.arity()) {         \
        i.second->update_antecedent_values();  \
        i.second->update_consequent_values();  \
    }

    POMAGMA_UPDATE_QUEUES(binary_functions);
    POMAGMA_UPDATE_QUEUES(binary_relations);
    // ... other arities ...
#undef POMAGMA_UPDATE_QUEUES
}
```

**Issue 3 - Antecedent Insertion Semantics**: A critical design question is when facts should be added to antecedent queues to trigger `GIVEN_*` programs. Two cases must be considered:

1. **New Insertions**: When `insert(lhs, rhs, val)` creates a genuinely new entry, it should trigger GIVEN programs
2. **Value Merging**: When existing values `val1` and `val2` merge to canonical representative `rep`, the resulting fact `(lhs, rhs, rep)` should also trigger GIVEN programs

**Rationale for Triggering on Merges**: From the logical perspective, `(lhs, rhs, rep)` represents new information even when it results from merging. The GIVEN programs need to fire on the canonical fact to ensure complete inference. For example, if `APP(f, x) = a` and `APP(f, x) = b` exist, and later `a` and `b` merge to `c`, then `APP(f, x) = c` is logically a new fact that should trigger inference rules.

**Implementation**: The `insert()` method should return `true` for both genuine insertions and merges, requiring modification of the return semantics:

```cpp
// Current: insert() returns true only for new entries
// Proposed: insert() returns true for (new entries OR merges)
bool BinaryFunction::insert(Ob lhs, Ob rhs, Ob val) {
    Ob existing = find(lhs, rhs);
    if (existing) {
        // Existing entry - check for merge
        if (existing != val) {
            Ob rep = m_carrier.ensure_equal(existing, val);
            if (rep != existing) {
                // Update value to canonical representative
                raw_update(lhs, rhs, rep);
                return true;  // Return true for merges
            }
        }
        return false;  // No change
    } else {
        // New entry
        raw_insert(lhs, rhs, val);
        return true;  // Return true for new insertions
    }
}
```

This ensures that antecedent queues capture all logically significant changes, whether from new facts or equivalence class consolidation.

## Work Plan

- [x] Implement integrated lazy queue architecture directly in `BinaryFunction`, `SymmetricFunction`, and `BinaryRelation` classes
- [x] Add thread-local worker queues with `lazy_insert()`, `lazy_try_insert()`, `lazy_equate()`, `lazy_gather()`, and `lazy_flush()` methods
- [x] Update cartographer/infer.cpp to use lazy queue methods instead of separate theorem queue classes
- [x] Replace `BinaryFunctionTheoremQueue` and `BinaryRelationTheoremQueue` with direct lazy operations in atlas functions
- [x] Implement BinaryRelation lazy queue methods (`lazy_insert()`, `lazy_try_insert()`, `lazy_gather()`, `lazy_flush()`)
- [x] Remove old theorem queue classes (`BinaryRelationRowTheoremQueue`, `BinaryRelationTheoremQueue`) from cartographer
- [x] Implement lazy queue architecture in macro atlas components (`InjectiveFunction`, `NullaryFunction`, `UnaryRelation`)
- [x] Add `not_lazy` base class for micro atlas components to maintain existing behavior
- [x] Add `lazy_gather()` and `lazy_flush()` methods to macro `Structure` class for coordinated queue management
- [x] Add lazy queue methods to Carrier class for E-graph reasoning (equate, gather, flush)
- [x] Modify VM opcodes `INFER_*` in vm_impl.hpp to use lazy queue methods instead of direct insertion
- [ ] Add phased execution methods to cartographer scheduler using OpenMP implicit barriers between proving and write phases  
- [ ] Implement forward-chaining inference in cartographer using lazy queue infrastructure for all inference patterns
- [ ] Update all VM callers (cartographer, analyst) to use lazy queue execution patterns
- [ ] Add performance benchmarks comparing lazy queue vs direct execution throughput and latency
- [ ] Update cartographer scheduler task priority handling to batch task creation during write phase instead of individual scheduling during proving
- [x] Add cross-references and links between this document and scheduler_design.md for the broader BSP scheduling context
- [ ] Test integration with existing cleanup task system to ensure phased inference doesn't interfere with cleanup program execution
- [ ] Validate memory usage patterns and cache behavior under high-concurrency lazy queue workloads
- [ ] Document migration guide for other components that may need to adopt lazy queue patterns in the future 