# Hybrid Incremental + Batch Inference for Surveyor

## Objective

Speed up surveyor inference by addressing the heaviest hitting rules: NLESS monotonicity.

## Background

### Benchmarking Data and Performance Hotspots

Recent benchmarking data from [`doc/benchmarks.md`](benchmarks.md) shows NLESS inference dominating surveyor execution time with 88.86% of total runtime spent in Line 6439 (1.44M calls). All hotspots involve inverse iteration using `VXx_Table::Iterator` with `tbb::concurrent_unordered_set<Ob>::const_iterator` under the hood.

The most expensive VM program operations in the NLESS inference are:
```
FOR_BINARY_FUNCTION_RHS_VAL COMP e d b       # 29.4% of runtime
FOR_BINARY_FUNCTION_LHS_VAL APP c e b        # 20.4% of runtime  
FOR_BINARY_FUNCTION_LHS_VAL COMP c e b       # 13.6% of runtime
FOR_BINARY_FUNCTION_RHS_VAL APP e d b        # 11.2% of runtime
FOR_SYMMETRIC_FUNCTION_LHS_VAL JOIN c e b    # 10.6% of runtime
```

These opcodes are defined in [`pomagma/atlas/program.hpp`](../pomagma/atlas/program.hpp) and execute inverse lookups like finding all `e` where `COMP e d = b`, which requires iterating through hash table buckets.

### Atlas Architecture Differences  

Surveyor uses atlas/micro with 16-bit identifiers and concurrent DenseSet operations optimized for incremental E-graph growth. The key files are:
- [`pomagma/atlas/micro/scheduler.hpp`](../pomagma/atlas/micro/scheduler.hpp) - Task scheduling and execution
- [`pomagma/atlas/micro/vm.hpp`](../pomagma/atlas/micro/vm.hpp) - VM implementation (includes atlas/vm.hpp)
- [`pomagma/atlas/micro/binary_relation.hpp`](../pomagma/atlas/micro/binary_relation.hpp) - Concurrent binary relations

Cartographer uses atlas/macro with 32-bit identifiers and implements efficient batch NLESS inference in [`pomagma/cartographer/infer.cpp`](../pomagma/cartographer/infer.cpp). The batch algorithms use sequential DenseSet operations for SIMD performance.

### Task Scheduling and VM Execution Flow

The surveyor's task execution follows this pattern:
1. Binary relation insertion (e.g., NLESS facts) triggers callbacks in [`pomagma/atlas/micro/binary_relation.cpp`](../pomagma/atlas/micro/binary_relation.cpp):
   ```cpp
   void BinaryRelation::insert_Lx(Ob i, Ob j) {
       if (not m_lines.Lx(i, j).fetch_one()) {
           _insert_Rx(i, j);
           m_insert_callback(i, j);  // Triggers task scheduling
       }
   }
   ```

2. Tasks are scheduled via functions in [`pomagma/atlas/micro/scheduler.cpp`](../pomagma/atlas/micro/scheduler.cpp):
   ```cpp
   void schedule(const NegativeOrderTask &task) {
       Scheduler::g_negative_order_tasks.push(task);
   }
   ```

3. The scheduler executes tasks using VM programs loaded from the compiler. VM execution happens in [`pomagma/atlas/vm_impl.hpp`](../pomagma/atlas/vm_impl.hpp) with program opcodes triggering the expensive inverse iteration patterns.

### Current NLESS Inference Implementation

The problem stems from sparsity: 96% of NLESS pairs are already proven, making most incremental checks wasteful. Yet batch inference only becomes efficient when processing substantial backlogs.

The cartographer's batch NLESS inference in [`pomagma/cartographer/infer.cpp`](../pomagma/cartographer/infer.cpp) implements multiple inference strategies:

```cpp
size_t infer_nless(Structure& structure) {
    // ... setup code ...
    for (Ob x = 1; x <= item_dim; ++x) {
        // ... filtering code ...
        for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
            Ob y = *iter;
            if (infer_nless_transitive(LESS, NLESS, x, y) or
                infer_nless_monotone(NLESS, APP, nonconst, x, y, z_set) or
                infer_nless_monotone(NLESS, COMP, nonconst, x, y, z_set) or
                (JOIN and infer_nless_monotone(NLESS, *JOIN, x, y, z_set)) or
                (RAND and infer_nless_monotone(NLESS, *RAND, x, y, z_set))) {
                theorems.push(x, y);
            }
        }
    }
}
```

This includes:
- `infer_nless_transitive()` - Handles transitivity rules `NLESS x z, LESS y z ⟹ NLESS x y`
- Multiple `infer_nless_monotone()` calls for APP, COMP, JOIN, and RAND functions implementing monotonicity rules

### VM Program Structure and Compilation

The compiler in [`pomagma/compiler/compiler.py`](../pomagma/compiler/compiler.py) generates VM programs with opcodes from [`pomagma/atlas/program.hpp`](../pomagma/atlas/program.hpp). Current opcodes include conditional execution like `IF_BLOCK`, `IF_BINARY_RELATION`, etc., but no global configuration opcodes.

The surveyor main entry point in [`pomagma/surveyor/survey_main.cpp`](../pomagma/surveyor/survey_main.cpp) calls either `Scheduler::survey()` or `Scheduler::survey_until_deadline()` which execute the main convergence loop.

## Design Overview

Implement threshold-based hybrid inference that monitors NLESS theorem queue size and dynamically switches between incremental and batch processing modes. Use VM conditional execution with global configuration variables to gate NLESS monotonicity rules without modifying the compiler's rule generation strategy.

When the queue remains small, continue incremental inference for responsiveness. When the queue grows large, disable incremental NLESS processing and trigger batch algorithms to efficiently drain the backlog. This avoids the performance cliff where batch phases repeatedly trigger with minimal work.

```cpp
while (has_work) {
    if (nless_queue_size < threshold) {
        vm.set_global_config(0, true);   // Enable incremental NLESS
        execute_incremental_tasks();
    } else {
        vm.set_global_config(0, false);  // Disable incremental, run batch
        run_batch_nless_inference();
    }
}
```

## Design Details

### VM Conditional Execution

The VM needs conditional opcodes that can skip program sections based on global boolean state. Add `IF_GLOBAL` opcode to the existing opcode enum in [`pomagma/atlas/program.hpp`](../pomagma/atlas/program.hpp):

```cpp
#define POMAGMA_OP_CODES(DO)                                                   \
    DO(PADDING, ({}))                                                          \
    DO(SEQUENCE, ({UINT8}))                                                    \
    // ... existing opcodes ...                                               \
    DO(IF_GLOBAL, ({UINT8}))                                                  \
    DO(INFER_SYMMETRIC_SYMMETRIC,                                              \
       ({SYMMETRIC_FUNCTION, OB, OB, SYMMETRIC_FUNCTION, OB, OB}))
```

Extend the VirtualMachine class in [`pomagma/atlas/vm.hpp`](../pomagma/atlas/vm.hpp) to support global configuration state:

```cpp
class VirtualMachine {
    std::array<bool, 256> m_global_config;
    
    void set_global_config(uint8_t index, bool value) {
        m_global_config[index] = value;
    }
};
```

The VM handler in [`pomagma/atlas/vm_impl.hpp`](../pomagma/atlas/vm_impl.hpp) follows the same pattern as other conditional opcodes:

```cpp
case IF_GLOBAL: {
    uint8_t config_id = pop_arg(program);
    if (m_global_config[config_id]) {
        _execute(program, context);  // Execute rest of this branch
    }
    // Otherwise skip this entire branch
} break;
```

### Scheduler Integration and Queue Monitoring

Modify the scheduler in [`pomagma/atlas/micro/scheduler.cpp`](../pomagma/atlas/micro/scheduler.cpp) to track NLESS task queue size. The existing `TaskQueue<NegativeOrderTask>` already handles NLESS tasks:

```cpp
namespace Scheduler {
    static std::atomic<size_t> g_nless_queue_size{0};
    static size_t g_nless_threshold = 1000;  // Configurable via environment
    
    void increment_nless_queue() {
        if (++g_nless_queue_size >= g_nless_threshold) {
            // Signal switch to batch mode
            get_vm().set_global_config(0, false);
        }
    }
}
```

Integrate tracking into the NLESS insertion pathway by extending the callback in [`pomagma/atlas/micro/binary_relation.cpp`](../pomagma/atlas/micro/binary_relation.cpp):

```cpp
void BinaryRelation::insert_Lx(Ob i, Ob j) {
    if (not m_lines.Lx(i, j).fetch_one()) {
        _insert_Rx(i, j);
        if (is_nless_relation()) {  // Check if this is NLESS relation
            Scheduler::increment_nless_queue();
        }
        m_insert_callback(i, j);
    }
}
```

### Compiler Integration

The compiler in [`pomagma/compiler/compiler.py`](../pomagma/compiler/compiler.py) should generate conditional NLESS programs by wrapping monotonicity sequences. Place the conditional right after the `GIVEN_BINARY_RELATION NLESS a b` line:

```cpp
// Generated program structure
GIVEN_BINARY_RELATION NLESS a b
SEQUENCE jump_to_next_rule
  IF_GLOBAL 0                        # Gate on config[0] - either execute branch or skip
    SEQUENCE
      FOR_SYMMETRIC_FUNCTION_VAL JOIN c d a
      FOR_SYMMETRIC_FUNCTION_LHS_VAL JOIN c e b
      INFER_BINARY_RELATION NLESS d e
    # ... more monotonicity sequences for APP, COMP, RAND
  next_rule_starts_here
```

### Batch NLESS Processing

Port the algorithms from [`pomagma/cartographer/infer.cpp`](../pomagma/cartographer/infer.cpp) to atlas/micro architecture. Create a new `BatchNlessInference` class that implements the efficient batch algorithms:

```cpp
class BatchNlessInference {
    Structure& m_structure;
    Scheduler& m_scheduler;
    
public:
    size_t run_batch_inference() {
        // Disable incremental NLESS processing
        get_vm().set_global_config(0, false);
        
        // Run adapted versions of cartographer algorithms
        size_t count = 0;
        count += infer_nless_transitive_batch();
        count += infer_nless_monotone_batch();
        
        // Reset queue size and re-enable incremental processing
        Scheduler::reset_nless_queue();
        get_vm().set_global_config(0, true);
        
        return count;
    }
};
```

The batch algorithms use embarrassingly parallel outer loops over E-classes with efficient set operations, avoiding the expensive inverse iteration that dominates incremental processing.

### Hybrid Convergence Loop

Modify the main survey loop in [`pomagma/surveyor/survey_main.cpp`](../pomagma/surveyor/survey_main.cpp) to support hybrid mode. Add a new `Scheduler::survey_hybrid()` function in [`pomagma/atlas/micro/scheduler.cpp`](../pomagma/atlas/micro/scheduler.cpp):

```cpp
void survey_hybrid() {
    BatchNlessInference batch_engine(structure, *this);
    
    while (has_work) {
        bool work_done = enforce_tasks_try_execute(true);
        
        if (g_nless_queue_size >= g_nless_threshold) {
            size_t theorems = batch_engine.run_batch_inference();
            POMAGMA_INFO("Batch inference proved " << theorems << " NLESS facts");
            work_done = true;
        }
        
        // Continue with sample and cleanup tasks
        work_done |= sample_tasks_try_execute(rng);
        work_done |= cleanup_tasks_try_execute();
        
        has_work = work_done || (get_pending_task_count() > 0);
    }
}
```

### Benchmarking and Threshold Tuning

Use the existing `profile_surveyor` command from [`pomagma/make.py`](../pomagma/make.py) to benchmark different threshold values:

```bash
# Baseline (pure incremental mode)
POMAGMA_NLESS_THRESHOLD=9999999999 python -m pomagma.make profile-surveyor theory=skja extra_size=1000 tool=time

# Test different hybrid thresholds
POMAGMA_NLESS_THRESHOLD=100  python -m pomagma.make profile-surveyor theory=skja extra_size=1000 tool=time
POMAGMA_NLESS_THRESHOLD=500  python -m pomagma.make profile-surveyor theory=skja extra_size=1000 tool=time  
POMAGMA_NLESS_THRESHOLD=1000 python -m pomagma.make profile-surveyor theory=skja extra_size=1000 tool=time
POMAGMA_NLESS_THRESHOLD=2000 python -m pomagma.make profile-surveyor theory=skja extra_size=1000 tool=time
```

The `POMAGMA_NLESS_THRESHOLD` environment variable controls when to switch from incremental to batch processing:
- Large values (e.g., `9999999999`) keep pure incremental mode for baseline comparison
- Smaller values enable hybrid behavior with different batch trigger points

Compare the execution times to find the optimal threshold for your workload size and theory.

## Work Plan

- [x] Add IF_GLOBAL opcode to [`pomagma/atlas/program.hpp`](../pomagma/atlas/program.hpp) and implement VM handler in [`pomagma/atlas/vm_impl.hpp`](../pomagma/atlas/vm_impl.hpp)
- [x] Extend VirtualMachine class in [`pomagma/atlas/vm.hpp`](../pomagma/atlas/vm.hpp) with global configuration state management
- [x] Modify [`pomagma/compiler/compiler.py`](../pomagma/compiler/compiler.py) to generate conditional NLESS programs with proper skip-byte calculation
- [ ] Add queue size tracking to [`pomagma/atlas/micro/scheduler.cpp`](../pomagma/atlas/micro/scheduler.cpp) and integrate with NLESS insertion callbacks
- [ ] Port cartographer's batch algorithms from [`pomagma/cartographer/infer.cpp`](../pomagma/cartographer/infer.cpp) to new BatchNlessInference class for atlas/micro
- [ ] Implement DenseSet mode selection supporting both concurrent and sequential variants for batch processing
- [ ] Create survey_hybrid() function in [`pomagma/atlas/micro/scheduler.cpp`](../pomagma/atlas/micro/scheduler.cpp) with threshold-based mode switching
- [ ] Extend [`pomagma/atlas/micro/binary_relation.cpp`](../pomagma/atlas/micro/binary_relation.cpp) to track NLESS-specific insertions
- [ ] Integrate hybrid mode selection in [`pomagma/surveyor/survey_main.cpp`](../pomagma/surveyor/survey_main.cpp) with environment variable control
- [ ] Benchmark hybrid system against baseline surveyor using existing `profile_surveyor` command and validate correctness across theories
