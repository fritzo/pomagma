# Unified E-graph Storage Design

This document analyzes Pomagma's multiple E-graph representations and proposes simplification through unification. The primary motivation is reducing maintenance complexity while accepting modest performance trade-offs where necessary to achieve substantial code simplification.

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

The macro atlas (`pomagma/atlas/macro/`) supports larger E-graphs with 32-bit identifiers (`typedef uint32_t Ob`) accommodating up to 4 billion E-classes. Binary functions (`pomagma/atlas/macro/binary_function.hpp`) use a simple hash map design with `ObPairMap m_values` storing `(lhs, rhs) -> val` mappings directly.

Three hash map configurations are configurable via `POMAGMA_USE_SPARSE_HASH`: Google's `sparse_hash_map` for memory efficiency, `dense_hash_map` for speed, or `std::unordered_map` as the default (`POMAGMA_USE_SPARSE_HASH == 0`). The macro implementation uses a single `std::mutex m_raw_mutex` for synchronization rather than fine-grained locking.

Hash computation (`pomagma/atlas/macro/util.hpp`) for 32-bit pairs uses `((x << 32) | y) * HASH_MULTIPLIER` with full 64-bit arithmetic, or simplified `(x << 32) | y` for `TrivialObPairHash`.



### Torch Representation

The torch layer (`pomagma/torch/structure.py`) uses multiple sparse representations for automatic differentiation. Each `BinaryFunction` stores four views: `LRv` as a `SparseBinaryFunction` using linear-probe hash tables for lookup, and `Vlr`, `Rvl`, `Lvr` as `SparseTernaryRelation` objects in Compressed Sparse Row format.

The CSR format uses `ptrs: torch.Tensor` of shape `[N+1]` as row pointers and `args: torch.Tensor` of shape `[nnz, 2]` containing argument pairs. Custom autograd functions (`BinaryFunctionSumProduct`) enable differentiable computation with gradient flows: `torch.ops.pomagma.binary_function_sum_product` for forward passes and separate backward passes through `Rvl` and `Lvr` indices.

The `SparseBinaryFunction` uses linear-probe hashing with `torch.ops.pomagma.hash_pair` and handles collisions through sequential probing in the hash table of shape `[H, 3]` storing `[lhs, rhs, val]` tuples.

## Component Usage Patterns

Source code analysis reveals the relationship between high-level interfaces and data structures across all Pomagma components:

### Components Using E-graph Storage

**Surveyor** (forward-chaining inference, `pomagma/surveyor/`) uses micro atlas exclusively. Files like `theory.cpp` and `insert_parser.hpp` include `pomagma/atlas/micro/structure_impl.hpp`. The atomic operations and tiled memory layout optimize for the write-heavy workload of growing E-graphs through concurrent exploration.

**Cartographer** (batch inference server, `pomagma/cartographer/`) uses macro atlas throughout. Files including `server.hpp`, `aggregate.cpp`, `infer.cpp`, `trim.cpp`, `collect_parser.hpp`, and `signature.cpp` all include `pomagma/atlas/macro/structure.hpp` or its implementation header. The 32-bit identifiers and hash map storage support aggregating multiple survey results and batch processing workflows.

**Analyst** (query engine, `pomagma/analyst/`) uses macro atlas for read-heavy operations. Files like `server.hpp`, `approximate.hpp`, `simplify.hpp`, `intervals.hpp`, and `propagate.cpp` include `pomagma/atlas/macro/structure.hpp`. The hash map storage and simple locking optimize complex constraint propagation and theorem proving queries.

**Theorist** (conjecture generation, `pomagma/theorist/`) uses macro atlas for comprehensive analysis. All major files (`assume.hpp`, `conjecture_diverge.hpp`, `conjecture_equal.hpp`, `consistency.hpp`, `hypothesize.hpp`, `find_parser.hpp`) include `pomagma/atlas/macro/structure.hpp` for analyzing large E-graphs during hypothesis formation. Standalone programs like `try_prove_nless_main.cpp` directly load and operate on macro atlas structures.

**Torch** (probabilistic computation, `pomagma/torch/`) uses its specialized CSR format optimized for vectorized operations and automatic differentiation. While it doesn't directly use atlas data structures, it loads atlas protobuf structures (`pomagma/atlas/structure.pb.h`) in `structure.cpp` and `io.py` for data conversion between formats.

### Components Not Using E-graph Storage

**Solver** (`pomagma/solver/`) implements an independent SMT solver for the Hstar theory with its own syntax representation (`syntax.hpp`, `theory_solver.hpp`). It operates on logical formulas rather than E-graph structures and has no atlas dependencies.

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

The unified E-graph design addresses Pomagma's maintenance complexity by creating an adaptive storage engine that automatically selects appropriate data structures based on workload characteristics. Rather than maintaining separate micro, macro, and torch implementations, the unified system adapts between storage formats (dense tiled arrays, sparse hash maps, vectorized tensors) based on density, access patterns, and scale. This approach prioritizes code simplification and maintainability, accepting modest performance trade-offs where necessary to achieve substantial reductions in implementation complexity.

## Design Details

### Motivation: Maintainability Through Simplification

The primary goal is reducing maintenance burden by consolidating redundant implementations. Pomagma currently maintains three distinct representations (micro, macro, torch), each with its own memory management, serialization, and validation logic. This creates substantial maintenance overhead: bug fixes must be replicated across implementations, performance optimizations benefit only specific use cases, and new developers face a steep learning curve understanding the relationships between representations.

Evidence of this complexity burden includes duplicated binary function implementations across `pomagma/atlas/micro/binary_function.hpp` and `pomagma/atlas/macro/binary_function.hpp`, each with different concurrency models, hash functions, and memory layouts serving similar fundamental purposes.

### Concurrency Strategy

The unified design builds on existing concurrency patterns rather than introducing new complexity. E-graph operations are naturally monotonic - adding E-classes and edges never invalidates existing data, only extends it. This property enables simpler synchronization strategies.

**Atomic operations for growth** leverage existing patterns in the micro atlas (`std::atomic<Ob>` with acquire/release semantics) for lock-free reads during most operations. Equivalence class merging uses compare-and-swap operations to maintain consistency without blocking readers.

**Isolated execution contexts** extend the existing VM pattern (`pomagma/atlas/vm.hpp`) where `VirtualMachine::execute` methods create contexts with local copies of relevant data. This provides query isolation without full MVCC overhead.

**Hierarchical locking for restructuring** protects major operations like format migration or compaction using the existing lock ordering (carrier, relations, functions) already established in the atlas implementations to prevent deadlocks.

### Adaptive Storage Strategy

The unified representation selects storage formats based on concrete measurable characteristics rather than abstract optimization goals. Dense regions where function tables are >50% populated benefit from micro-style tiled arrays that optimize cache locality. Sparse regions where <10% of function applications are defined benefit from macro-style hash maps that avoid storing undefined entries.

**Format selection criteria** include density (ratio of defined to possible function applications), access patterns (random vs. sequential), and scale (memory constraints). These metrics can be measured during operation and trigger format migrations when beneficial.

**Lazy index construction** builds on existing patterns where inverse indices (`Vlr_Table`, `VLr_Table`, `VRl_Table`) are populated on demand during binary function insertions. The unified approach extends this by making index materialization completely demand-driven with eviction based on usage patterns rather than maintaining all indices simultaneously.

### Implementation Challenges

**Interface abstraction** requires designing virtual iterators that can traverse both dense tile structures and sparse hash maps efficiently. The existing iterator patterns in `BinaryFunction::iter_lhs()` and `BinaryFunction::iter_rhs()` provide templates for unified iteration interfaces.

**Migration mechanics** must handle transitions between storage formats without corrupting ongoing operations. This can build on existing compaction logic in the cartographer (`pomagma/cartographer/trim.cpp`) that already handles structural reorganization of atlas data.

**Memory management** across different allocators (tiled arrays vs. hash maps vs. tensor storage) requires careful coordination to avoid fragmentation. The existing aligned allocation utilities (`pomagma/util/aligned_alloc.hpp`) provide building blocks for unified memory management.

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
- [ ] Create unified `EGraphInterface` abstract base class with iterator and mutation methods from existing `BinaryFunction` classes
- [ ] Implement `MicroAtlasAdapter` and `MacroAtlasAdapter` wrapper classes that expose unified interface over current implementations
- [ ] Add benchmarking harness comparing adapter performance against direct atlas usage to establish baseline metrics
- [ ] Create format detection logic measuring density and access patterns to guide storage format selection
- [ ] Implement unified `BinaryFunction` class that delegates to appropriate adapter based on runtime characteristics
- [ ] Add lazy index materialization extending existing on-demand inverse index patterns with LRU eviction
- [ ] Create format migration mechanisms building on existing compaction and trim operations for consistency
- [ ] Extend concurrency model using existing atomic operations and VM context patterns for reader isolation
- [ ] Integrate torch CSR representation as additional adapter option within unified framework
- [ ] Migrate surveyor, cartographer, analyst, and theorist components incrementally to use unified interface 