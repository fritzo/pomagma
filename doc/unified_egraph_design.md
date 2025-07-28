# Unified E-graph Storage Design

This document analyzes Pomagma's multiple E-graph representations and proposes simplification through unification and architectural consolidation. The primary motivation is enabling a unified workflow where users can perform complete analysis pipelines (E-graph growth → incremental inference → batch inference → querying → conjecturing → language optimization → analytics extraction) against a single database instance in a single Python script. 

**NEW DIRECTION:** The design has evolved towards eliminating the surveyor entirely and consolidating all inference capabilities into the cartographer. This eliminates the maintenance burden of dual atlas implementations (micro/macro) and the TBB dependency while providing a single, scalable inference engine with phased execution.

## Background: Current State of the System

### Memory Requirements and Scaling

Production E-graphs exhibit superlinear memory growth due to dense binary function tables. Based on empirical observations from Pomagma's usage patterns:

| E-graph Size      | Memory Usage | Storage Space | Compute Time |
|-------------------|--------------|---------------|--------------|
| 1,000 E-classes   | ~10MB        | ~1MB          | ~1 CPU hour  |
| 10,000 E-classes  | ~1GB         | ~100MB        | ~1 CPU week  |
| 100,000 E-classes | ~100GB       | ~10GB         | ~1 CPU year  |

Memory requirements grow superlinearly, approaching O(N²) for dense binary function representations where each function potentially stores N² entries. Storage requirements grow more slowly due to compression and the sparsity of actual E-graph connections. The quadratic memory bottleneck motivates the need for adaptive storage strategies.

## E-graph Storage Implementations

**DEPRECATION NOTICE:** The micro atlas implementation is being eliminated in favor of a unified cartographer-based approach. This section documents the current state before consolidation.

### Atlas Micro Implementation (TO BE REMOVED)

The micro atlas (`pomagma/atlas/micro/`) targets high-performance concurrent access with 16-bit identifiers (`typedef uint16_t Ob`) supporting up to 65,535 E-classes. Data is organized in 8×8 tiles of 64 elements each (`LOG2_ITEMS_PER_TILE = 3`), optimized for cache locality. Each tile occupies exactly two 64-byte cache lines, with traversal patterns favoring fixed-left-hand-side while varying right-hand-side access.

Binary functions (`pomagma/atlas/micro/binary_function.hpp`) maintain four index structures per function: `m_tiles` for tiled storage and three inverse indices (`m_Vlr_table`, `m_VLr_table`, `m_VRl_table`) using Intel TBB concurrent data structures. The `Vlr_Table` uses `tbb::concurrent_unordered_set<std::pair<Ob, Ob>>` while `VXx_Table` uses `tbb::concurrent_unordered_map`. All operations use `std::atomic<Ob>` with `acquire`/`release` semantics for lock-free reads and atomic writes.

Hash computation (`pomagma/atlas/micro/inverse_bin_fun.hpp`) uses multiplicative hashing with `HASH_MULTIPLIER = 11400714819323198485ULL`, applied as `((x << 16) | y) * HASH_MULTIPLIER` for 16-bit pairs.

**The micro atlas and TBB dependency will be completely removed in favor of the enhanced cartographer architecture.**

### Atlas Macro Implementation

The macro atlas (`pomagma/atlas/macro/`) supports E-graphs with 16-bit identifiers by default (`typedef uint16_t Ob`) accommodating up to 65K E-classes. Binary functions (`pomagma/atlas/macro/binary_function.hpp`) use a simple hash map design with `ObPairMap m_values` storing `(lhs, rhs) -> val` mappings directly.

Three hash map configurations are configurable via `POMAGMA_USE_SPARSE_HASH`: Google's `sparse_hash_map` for memory efficiency, `dense_hash_map` for speed, or `std::unordered_map` as the default (`POMAGMA_USE_SPARSE_HASH == 0`). The macro implementation uses a single `std::mutex m_raw_mutex` for synchronization rather than fine-grained locking.

Hash computation (`pomagma/atlas/macro/util.hpp`) for 16-bit pairs uses an improved xxHash-inspired algorithm with better distribution than simple concatenation.

### Torch Representation

The torch layer (`pomagma/torch/structure.py`) uses multiple sparse representations for automatic differentiation. Each `BinaryFunction` stores four views: `LRv` as a `SparseBinaryFunction` using linear-probe hash tables for lookup, and `Vlr`, `Rvl`, `Lvr` as `SparseTernaryRelation` objects in Compressed Sparse Row format.

The CSR format uses `ptrs: torch.Tensor` of shape `[N+1]` as row pointers and `args: torch.Tensor` of shape `[nnz, 2]` containing argument pairs. Custom autograd functions (`BinaryFunctionSumProduct`) enable differentiable computation with gradient flows: `torch.ops.pomagma.binary_function_sum_product` for forward passes and separate backward passes through `Rvl` and `Lvr` indices.

The `SparseBinaryFunction` uses linear-probe hashing with `torch.ops.pomagma.hash_pair` and handles collisions through sequential probing in the hash table of shape `[H, 3]` storing `[lhs, rhs, val]` tuples.

## Component Usage Patterns

Source code analysis reveals the relationship between high-level interfaces and data structures across all Pomagma components:

### Components Using E-graph Storage

**Surveyor** (forward-chaining inference, `pomagma/surveyor/`) **TO BE REMOVED** - Currently uses micro atlas exclusively. Files like `theory.cpp` and `insert_parser.hpp` include `pomagma/atlas/micro/structure_impl.hpp`. The atomic operations and tiled memory layout optimize for the write-heavy workload of growing E-graphs through concurrent exploration. **All surveyor functionality will be migrated to the enhanced cartographer.**

**Cartographer** (batch inference server, `pomagma/cartographer/`) uses macro atlas throughout and **will become the primary inference engine**. Files including `server.hpp`, `aggregate.cpp`, `infer.cpp`, `trim.cpp`, `collect_parser.hpp`, and `signature.cpp` all include `pomagma/atlas/macro/structure.hpp` or its implementation header. The 16-bit identifiers and hash map storage support aggregating multiple survey results and batch processing workflows. **The cartographer will be enhanced with a new scheduler supporting complete forward-chaining inference and phased execution.**

**Analyst** (query engine, `pomagma/analyst/`) uses macro atlas for read-heavy operations. Files like `server.hpp`, `approximate.hpp`, `simplify.hpp`, `intervals.hpp`, and `propagate.cpp` include `pomagma/atlas/macro/structure.hpp`. The hash map storage and simple locking optimize complex constraint propagation and theorem proving queries.

**Theorist** (conjecture generation, `pomagma/theorist/`) uses macro atlas for comprehensive analysis. All major files (`assume.hpp`, `conjecture_diverge.hpp`, `conjecture_equal.hpp`, `consistency.hpp`, `hypothesize.hpp`, `find_parser.hpp`) include `pomagma/atlas/macro/structure.hpp` for analyzing large E-graphs during hypothesis formation. Standalone programs like `try_prove_nless_main.cpp` directly load and operate on macro atlas structures.

**Torch** (probabilistic computation, `pomagma/torch/`) uses its specialized CSR format optimized for vectorized operations and automatic differentiation. While it doesn't directly use atlas data structures, it loads atlas protobuf structures (`pomagma/atlas/structure.pb.h`) in `structure.cpp` and `io.py` for data conversion between formats.

### Components Not Using E-graph Storage

**Linguist** (`pomagma/linguist/`) focuses on language model fitting and grammar optimization without direct E-graph manipulation, operating at a higher abstraction level.

**Corpus** (`pomagma/corpus/`) manages literate code representations in combinatory algebra without requiring low-level E-graph access.

**Examples** (`pomagma/examples/`) contains applications that use high-level interfaces (typically analyst clients) rather than direct atlas access.

**Language** (`pomagma/language/`) implements probabilistic grammar representations independent of specific E-graph storage formats.

**Compiler** (`pomagma/compiler/`) generates inference rules and strategies but operates on abstract syntax representations rather than atlas data structures.

**IO** (`pomagma/io/`) provides serialization utilities and message passing infrastructure that supports atlas formats but doesn't directly manipulate E-graph structures.

**Reducer** (`pomagma/reducer/`) implements λ-calculus interpreters with extensive unit tests, operating on abstract syntax trees rather than E-graph representations.

## Related Work: Database Alternatives

### Performance Cost Analysis

Replacing Pomagma's specialized data structures with an existing database would incur significant performance penalties. Traditional databases add substantial overhead through tuple headers, B-tree indices, transaction logs, and query planning that are unnecessary for E-graph operations.

Pomagma's profiling infrastructure (`pomagma/util/profiler.cpp`, `ProgramProfiler`) shows that critical paths like binary function operations dominate execution time. Benchmarks in `doc/benchmarks.md` demonstrate that inference operations process millions of facts per second, with line 4837 handling 17,980,658 calls consuming 59% of execution time at 0.01 seconds per call. This performance depends critically on cache-optimized data layouts and lock-free operations.

Relational databases would struggle with E-graph workloads because they optimize for different access patterns: range queries over sorted data rather than hash-based lookups, ACID transactions rather than monotonic updates, and SQL query planning rather than compiled inference rules. Column stores might better match the analytical workload but would still add parsing and optimization overhead inappropriate for tight inference loops.

### Memory Overhead Assessment

Graph databases store general-purpose property graphs with edge and vertex attributes, requiring additional metadata that E-graphs don't need. Pomagma's equivalence classes and function applications have specific semantics that don't map naturally to property graphs, requiring encoding overhead.

### Code Complexity Comparison

Reimplementing Pomagma's inference algorithms in SQL would face impedance mismatches between set-based operations and the recursive, fixed-point computations that dominate E-graph inference. While possible, the result would be less readable and harder to optimize than the current hand-tuned C++ implementations.

Datalog engines like Soufflé would be more natural for recursive inference patterns but would lose the fine-grained control over memory layout, concurrency, and cache optimization that Pomagma's current implementations provide for performance-critical paths.

## Design Overview

The unified E-graph design eliminates Pomagma's architectural complexity by consolidating all inference capabilities into a single cartographer-based system. Rather than maintaining separate surveyor (micro atlas) and cartographer (macro atlas) implementations with different concurrency models and storage strategies, the new design provides a single, enhanced cartographer that supports:

1. **Complete forward-chaining inference** through a new scheduler implementation (based on `pomagma/surveyor/scheduler.cpp` patterns)
2. **Phased inference execution** using the proven theorem queue architecture from `doc/theorem_queue.md`
3. **Lazy inverse binary function tables** constructed as optimized read-only CSR tables per inference phase
4. **Unified client interface** with a new `.survey()` method for database growth and saturation

This eliminates the TBB dependency, removes the micro atlas maintenance burden, and provides a single scalable inference engine that can handle both incremental database growth and large-scale batch operations through the same optimized infrastructure.

### Key Architectural Benefits

1. **Simplified Maintenance**: Eliminates dual atlas implementations (micro/macro) and their separate concurrency models, testing requirements, and optimization needs
2. **Unified Workflow**: Users can perform complete analysis pipelines through a single cartographer client without transferring data between different systems
3. **Reduced Dependencies**: Removes Intel TBB dependency, simplifying builds and deployments
4. **Enhanced Scalability**: The cartographer's hash-map based storage scales better than micro atlas's tiled arrays for large databases
5. **Proven Inference**: Incorporates the surveyor's complete inference capabilities through the scheduler and theorem queue architecture
6. **Lazy Optimization**: Inverse tables are constructed only when needed and optimized for specific inference phases

## Design Details

### Motivation: Maintainability Through Simplification

The primary goal is reducing maintenance burden by consolidating redundant implementations. Pomagma currently maintains three distinct representations (micro, macro, torch), each with its own memory management, serialization, and validation logic. This creates substantial maintenance overhead: bug fixes must be replicated across implementations, performance optimizations benefit only specific use cases, and new developers face a steep learning curve understanding the relationships between representations.

Evidence of this complexity burden includes duplicated binary function implementations across `pomagma/atlas/micro/binary_function.hpp` and `pomagma/atlas/macro/binary_function.hpp`, each with different concurrency models, hash functions, and memory layouts serving similar fundamental purposes.

### Header-Based Polymorphism Pattern

The current system uses a "header-based polymorphism" pattern to support different `Ob` identifier widths through parallel directory hierarchies (`micro/` vs `macro/`). This approach provides identical class interfaces with different underlying implementations:

**Micro Atlas** (`uint16_t Ob`):
- Supports up to 65,535 E-classes
- Uses tiled atomic arrays optimized for concurrent access
- Includes inverse lookup tables (`POMAGMA_HAS_INVERSE_INDEX = 1`)

**Macro Atlas** (`uint16_t Ob`):
- Supports up to 65K E-classes  
- Uses hash maps with configurable backends
- No inverse lookup tables (`POMAGMA_HAS_INVERSE_INDEX = 0`)

The pattern works by having each directory define its own `util.hpp` with different `typedef Ob` definitions, while client code includes headers from the appropriate directory. Identical class names (`BinaryFunction`, `Carrier`) resolve to different implementations based on the include path, with shared template code using conditional compilation for variant-specific features.

### Concurrency Strategy

The unified design builds on existing concurrency patterns rather than introducing new complexity. E-graph operations are naturally monotonic - adding E-classes and edges never invalidates existing data, only extends it. This property enables simpler synchronization strategies.

**Atomic operations for growth** leverage existing patterns in the micro atlas (`std::atomic<Ob>` with acquire/release semantics) for lock-free reads during most operations. Equivalence class merging uses compare-and-swap operations to maintain consistency without blocking readers.

**Isolated execution contexts** extend the existing VM pattern (`pomagma/atlas/vm.hpp`) where `VirtualMachine::execute` methods create contexts with local copies of relevant data. This provides query isolation without full MVCC overhead.

**Hierarchical locking for restructuring** protects major operations like format migration or compaction using the existing lock ordering (carrier, relations, functions) already established in the atlas implementations to prevent deadlocks.

### On-Demand Index Construction Strategy

The unified representation builds storage formats and indices only when required by specific operations, prioritizing predictability over automatic optimization. The system follows a "follow-the-user" workflow where data structures are constructed in response to user actions rather than preemptive heuristics.

**Identifier Width** is now standardized at 16-bit for all components:
- **16-bit mode** (`uint16_t Ob`): All components use up to 65K E-classes with configurable `POMAGMA_OB_BITWIDTH=16`
- **32-bit mode** (`uint32_t Ob`): Vestigial support remains in codebase but is not actively used

**Index Construction Triggers** follow operation requirements:
- **Inverse lookup tables** (`Vlr_Table`, `VLr_Table`, `VRl_Table`) are built when VM programs require inverse queries (`FOR_BINARY_FUNCTION_VAL`, etc.)  
- **Torch CSR indices** are constructed on-demand for analytics operations and torn down immediately after mutations
- **Storage strategy** uses hash maps for all binary functions regardless of identifier width

**Index Invalidation** follows mutation semantics:
- Any structural modification (insert, merge) invalidates dependent read-only indices
- Torch CSR indices are immediately discarded on any mutation
- Inverse lookup tables can be incrementally maintained or rebuilt depending on operation frequency

This approach eliminates unpredictable format switching while ensuring that expensive indices are only maintained when actively needed.

### Performance-Critical Interface Design

**Bottleneck Analysis** reveals three distinct performance tiers requiring different abstraction strategies:

1. **VM Program Execution** (17.9M calls, 59% execution time): Both surveyor forward-chaining and analyst solving (`client.solve()`, `validate_facts()`) generate VM programs that execute operations like `fun.find(lhs, rhs)`, `fun.iter_lhs(lhs)`, and `fun.insert(lhs, rhs, val)` in tight loops requiring zero-cost abstraction
2. **Cartographer Batch Inference**: Parallel algorithms for transitivity, monotonicity, and convexity with intensive `DenseSet` operations, binary function lookups, and OpenMP parallelization - core E-graph reasoning functionality  
3. **Session Management**: High-level operations like `load()`, `dump()`, `execute_program()` can afford virtual dispatch
4. **Torch Analytics**: CSR-based operations for language modeling and analytics that can be built on-demand as needed

**Two-Tier Interface Strategy**:
- **High-level virtual interface** (`EGraphSession`) for infrequent session/structure operations where virtual dispatch is acceptable
- **Zero-cost inner interface** using templates or `std::variant` for hot-path operations (binary function lookups, iteration, insertion)

**Compilation Strategy** now standardized for 16-bit identifiers across all components:
- `vm_micro.cpp` - VM execution (surveyor + analyst) using 16-bit identifiers
- `vm_macro.cpp` - VM execution (surveyor + analyst) using 16-bit identifiers with hash storage  
- `cartographer_micro.cpp` - Batch inference algorithms using 16-bit identifiers
- `cartographer_macro.cpp` - Batch inference algorithms using 16-bit identifiers
- `torch_csr.cpp` - Analytics operations specialized for CSR tensor indices (lower priority)

**Index Management** coordinates expensive auxiliary indices through the high-level interface:
- Inverse lookup tables built on-demand when VM programs require `FOR_BINARY_FUNCTION_VAL` operations
- Torch CSR indices constructed for analytics operations and discarded after mutations
- Session tracks which indices are active and invalidates them atomically during structural modifications

This approach ensures that hot paths maintain current performance characteristics while providing unified workflow capabilities through careful abstraction boundary design.

### In-Process vs Client-Server Architecture

Pomagma exhibits an architectural mismatch between its predominantly client-server design and torch's in-process requirements. The surveyor, cartographer, and analyst follow a server-client pattern with ZMQ messaging (`pomagma/cartographer/server.py`, `pomagma/analyst/server.py`) that enables distributed computation and resource isolation. However, torch requires in-process access to tensor data for PyTorch's automatic differentiation and GPU acceleration.

Several resolution strategies are possible:

**Embedded database approach** would modify atlas servers to expose a C API that torch can link against directly. This allows torch to access atlas data structures in-process while preserving the server architecture for other clients. The challenge is managing memory ownership and ensuring thread safety across the boundary.

**Shared memory interface** could use memory-mapped files or POSIX shared memory to allow torch direct access to atlas data without copying. The atlas server would memory-map its data structures, with torch accessing them read-only for tensor operations. This preserves isolation while enabling zero-copy access.

**Hybrid architecture** would maintain both interfaces - the existing ZMQ servers for Python clients and distributed operations, plus an embedded interface specifically for torch. The atlas would expose different APIs optimized for each use case: message-based for network clients, direct memory access for in-process computation.

**Unified in-process design** would eliminate the client-server split entirely, running all components as libraries within the same process. This simplifies the architecture and enables torch-style direct memory access throughout, but loses the benefits of distributed computation and process isolation that the current design provides.

The hybrid approach appears most promising, allowing torch to access data in-process for performance while preserving the distributed architecture for other use cases.

## Work Plan

The refactoring strategy follows an incremental approach where each step is fully tested and documented before proceeding. The system remains working throughout, with the surveyor elimination as the final step.

### Step 1: Add Cartographer Survey Interface (Minimal Implementation)
- [ ] Add `.survey(chunk_size=512)` method to `pomagma/cartographer/client.py:Client` class
- [ ] Update `pomagma/cartographer/cartographer_messages.proto` with `Survey` message containing `chunk_size` parameter
- [ ] Add `survey()` method to `pomagma/cartographer/server.hpp` and `server.cpp` that initially delegates to existing `infer()` methods
- [ ] Write unit tests for new client/server survey interface
- [ ] Update `doc/client.md` to document the new `.survey()` method
- [ ] **Git commit:** "Add basic cartographer survey interface"

### Step 2: Implement Lazy Inverse Binary Function Tables
- [ ] Add lazy CSR (Compressed Sparse Row) inverse table infrastructure to `pomagma/atlas/macro/binary_function.hpp`
- [ ] Implement `build_inverse_tables()` and `clear_inverse_tables()` methods with proper lifecycle management
- [ ] Add unit tests for CSR table construction, access patterns, and invalidation
- [ ] Optimize CSR construction for read-only sequential access during inference phases
- [ ] **Git commit:** "Add lazy inverse tables to macro atlas"

### Step 3: Implement Cartographer Scheduler Infrastructure
- [ ] Create `pomagma/cartographer/scheduler.hpp` and `scheduler.cpp` based on proven surveyor patterns
- [ ] Implement basic `Agenda` class with priority queues for task management (MergeTask, EnforceTask, SampleTask, CleanupTask)
- [ ] Add `WorkStealingDeque` and `ThreadBarrier` classes for phased execution
- [ ] Write comprehensive unit tests for scheduler components
- [ ] **Git commit:** "Add cartographer scheduler infrastructure"

### Step 4: Integrate Theorem Queues and Phased Execution
- [ ] Integrate lazy theorem queue architecture into cartographer scheduler
- [ ] Implement phased execution (proving phase → write phase) using OpenMP barriers
- [ ] Update VM opcodes in `vm_impl.hpp` to support both direct writes (existing) and lazy queues (new) via compile-time flag
- [ ] Add integration tests for phased inference execution
- [ ] **Git commit:** "Add theorem queue and phased execution to cartographer"

### Step 5: Implement Complete Survey Functionality
- [ ] Enhance cartographer `survey()` method with actual database growth logic using PCFG sampling
- [ ] Integrate scheduler with survey operations for complete forward-chaining inference
- [ ] Add saturation detection and chunk-based growth to reach target database size
- [ ] Create comprehensive integration tests comparing cartographer survey results with surveyor results
- [ ] **Git commit:** "Implement complete survey functionality in cartographer"

### Step 6: Add Experimental Survey Mode to Main Commands
- [ ] Add `POMAGMA_USE_CARTOGRAPHER_SURVEY=1` environment variable to `pomagma/__main__.py`
- [ ] Modify `init()`, `explore()`, and `make()` commands to optionally use cartographer survey instead of surveyor
- [ ] Ensure both paths work and produce equivalent results
- [ ] Add integration tests for both surveyor and cartographer workflows
- [ ] Update documentation to describe experimental mode
- [ ] **Git commit:** "Add experimental cartographer survey mode to main commands"

### Step 7: Switch Default to Cartographer Survey
- [ ] Change default behavior in `pomagma/__main__.py` to use cartographer survey
- [ ] Add `POMAGMA_USE_LEGACY_SURVEYOR=1` fallback environment variable for compatibility
- [ ] Run full test suite with new default, ensuring no regressions
- [ ] Update user documentation to reflect new default behavior
- [ ] **Git commit:** "Switch default to cartographer survey with legacy fallback"

### Step 8: Remove Surveyor Fallback and Legacy Code
- [ ] Remove legacy surveyor usage from `pomagma/__main__.py`, `pomagma/workers.py`, `pomagma/make.py`
- [ ] Remove `POMAGMA_USE_LEGACY_SURVEYOR` environment variable and associated code paths
- [ ] Update all documentation to remove surveyor references
- [ ] Run full test suite to ensure clean removal
- [ ] **Git commit:** "Remove surveyor fallback and legacy code paths"

### Step 9: Delete Surveyor Implementation
- [ ] Delete `pomagma/surveyor/` directory entirely (`.cpp`, `.hpp`, `CMakeLists.txt`, Python `__init__.py`)
- [ ] Remove surveyor CMake targets and build dependencies
- [ ] Update any remaining surveyor references in examples or documentation
- [ ] **Git commit:** "Delete surveyor implementation"

### Step 10: Delete Micro Atlas and TBB Dependency
- [ ] Delete `pomagma/atlas/micro/` directory entirely
- [ ] Remove micro atlas CMake targets and dependencies from build system
- [ ] Remove Intel TBB from CMake dependencies and vcpkg requirements
- [ ] Remove all `#include <tbb/*.hpp>` references from remaining codebase
- [ ] Update build documentation to reflect simplified dependencies
- [ ] **Git commit:** "Remove micro atlas and TBB dependency"

### Step 11: Final Documentation and Architecture Updates
- [ ] Update `doc/README.md` to reflect new single-engine architecture
- [ ] Update architecture diagrams and component descriptions throughout documentation
- [ ] Create migration guide documenting the transition from dual-engine to single-engine architecture
- [ ] Update benchmarking documentation to focus on cartographer performance
- [ ] **Git commit:** "Update documentation for unified cartographer architecture"

Each step includes comprehensive testing at the appropriate level (unit, integration, or system tests) and maintains full backward compatibility until the final removal steps. The system remains functional and well-documented throughout the entire transition. 