# Unified E-graph Storage Design

This document analyzes Pomagma's multiple E-graph representations and proposes simplification through unification. The primary motivation is enabling a unified workflow where users can perform complete analysis pipelines (E-graph growth → incremental inference → batch inference → querying → conjecturing → language optimization → analytics extraction) against a single database instance in a single Python script. This requires both reducing maintenance complexity of multiple storage formats and providing a consistent interface that supports all use cases without requiring users to manually transfer data between different storage systems.

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

Pomagma implements three distinct atlas data structures and a separate torch representation, each optimized for different scenarios.

### Atlas Micro Implementation

The micro atlas (`pomagma/atlas/micro/`) targets high-performance concurrent access with 16-bit identifiers (`typedef uint16_t Ob`) supporting up to 65,535 E-classes. Data is organized in 8×8 tiles of 64 elements each (`LOG2_ITEMS_PER_TILE = 3`), optimized for cache locality. Each tile occupies exactly two 64-byte cache lines, with traversal patterns favoring fixed-left-hand-side while varying right-hand-side access.

Binary functions (`pomagma/atlas/micro/binary_function.hpp`) maintain four index structures per function: `m_tiles` for tiled storage and three inverse indices (`m_Vlr_table`, `m_VLr_table`, `m_VRl_table`) using Intel TBB concurrent data structures. The `Vlr_Table` uses `tbb::concurrent_unordered_set<std::pair<Ob, Ob>>` while `VXx_Table` uses `tbb::concurrent_unordered_map`. All operations use `std::atomic<Ob>` with `acquire`/`release` semantics for lock-free reads and atomic writes.

Hash computation (`pomagma/atlas/micro/inverse_bin_fun.hpp`) uses multiplicative hashing with `HASH_MULTIPLIER = 11400714819323198485ULL`, applied as `((x << 16) | y) * HASH_MULTIPLIER` for 16-bit pairs.

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

**Surveyor** (forward-chaining inference, `pomagma/surveyor/`) uses micro atlas exclusively. Files like `theory.cpp` and `insert_parser.hpp` include `pomagma/atlas/micro/structure_impl.hpp`. The atomic operations and tiled memory layout optimize for the write-heavy workload of growing E-graphs through concurrent exploration.

**Cartographer** (batch inference server, `pomagma/cartographer/`) uses macro atlas throughout. Files including `server.hpp`, `aggregate.cpp`, `infer.cpp`, `trim.cpp`, `collect_parser.hpp`, and `signature.cpp` all include `pomagma/atlas/macro/structure.hpp` or its implementation header. The 16-bit identifiers and hash map storage support aggregating multiple survey results and batch processing workflows.

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

The unified E-graph design addresses Pomagma's maintenance complexity by creating a flexible storage engine that constructs indices and storage formats on-demand based on user operations. Rather than maintaining separate micro, macro, and torch implementations, the unified system provides a single interface that can utilize different storage formats (dense tiled arrays, sparse hash maps, vectorized tensors) as needed by specific operations. The system follows a "follow-the-user" workflow: when users attempt operations requiring specific indices, those indices are built on-demand; when mutations invalidate indices, they are removed. This approach prioritizes predictability and user control while enabling the full range of Pomagma operations against a single database instance.

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

## Implementation Plan

The refactoring strategy prioritizes incremental migration to maintain system functionality throughout the transition. The approach uses an adapter pattern initially, allowing existing components to continue working while gradually introducing unified interfaces. This minimizes risk and enables rollback at each stage.

Implementation tasks in dependency order:

- [x] Remove abandoned shard atlas implementation (`pomagma/atlas/shard/` directory and CMake references) to simplify unification scope
- [ ] Create high-level `EGraphSession` virtual interface for session management (load/dump/execute_program) where virtual dispatch is acceptable
- [ ] Implement zero-cost inner `Structure<StoragePolicy>` template for hot-path operations (find/iter/insert) using compile-time dispatch
- [ ] Create storage policy classes (`MicroStoragePolicy`, `MacroStoragePolicy`) encapsulating Ob types and core data structures  
- [ ] Compile VM execution against all storage policies in separate translation units (vm_micro.cpp, vm_macro.cpp) for surveyor and analyst operations
- [ ] Compile cartographer batch inference against all storage policies (cartographer_micro.cpp, cartographer_macro.cpp) for core reasoning algorithms
- [ ] Add session management layer with identifier width selection at startup and index tracking
- [ ] Implement on-demand inverse index construction in session layer triggered by VM program analysis (`FOR_BINARY_FUNCTION_VAL` detection)
- [ ] Add atomic index invalidation system coordinated through session layer during structural modifications
- [ ] Create torch CSR storage policy (`TorchStoragePolicy`) and compile analytics operations (torch_csr.cpp) for on-demand ML workflows
- [ ] Implement benchmarking harness measuring compilation time vs. runtime performance trade-offs for template specialization approach
- [ ] Create operation pattern tracking in session layer to optimize index lifetime decisions (build/cache/discard)
- [ ] Migrate surveyor, cartographer, analyst, and theorist to use session interface with appropriate storage policy selection
- [ ] Add unified Python API that provides single-script workflow capabilities while preserving performance through proper abstraction boundaries 