# Design Doc: Large Finitary Joins

## Objective

Replace chains of binary JOIN operations with single finitary join expressions to reduce E-class creation overhead and improve performance for large disjunctive expressions.

## Background

JOIN is currently implemented as a binary commutative and associative operation across Pomagma's components, with different representations optimized for specific use cases. The core challenge is that creating large disjunctive expressions like `JOIN(x[0], JOIN(x[1], ..., JOIN(x[n-2], x[n-1])...))` requires creating 999 intermediate E-classes and corresponding binary function table entries to represent a 1000-part join, imposing significant memory and inference overhead.

### Current JOIN Implementations

**Atlas Storage** (`pomagma/atlas/macro/symmetric_function.hpp`, `pomagma/atlas/micro/symmetric_function.hpp`): JOIN is stored as a symmetric binary function using either hash maps (macro) or tiled atomic arrays (micro). Binary functions dominate E-graph memory usage, with `O(N²)` worst-case storage for N E-classes. The atlas structures support efficient lookup, insertion, and iteration through `find(lhs, rhs)`, `iter_lhs(lhs)`, and inverse operations when `POMAGMA_HAS_INVERSE_INDEX` is enabled.

**Virtual Machine Execution** (`pomagma/atlas/vm_impl.hpp`): VM programs compile constraint satisfaction queries into bytecode that operates on binary and symmetric functions through opcodes like `FOR_SYMMETRIC_FUNCTION_LHS`, `FOR_SYMMETRIC_FUNCTION_VAL`, and `INFER_SYMMETRIC_FUNCTION`. These operations form the performance-critical path for both surveyor forward-chaining and analyst solving, processing millions of operations per second according to profiling data in `doc/benchmarks.md`.

**Reducer Syntax** (`pomagma/reducer/syntax.py`, `pomagma/reducer/bohm.py`): The reducer represents JOIN as binary terms using `JOIN(lhs, rhs)` constructors, with helper functions like `iter_join` for flattening and `join_set` for handling collections. However, `join_set` ultimately converts collections back to nested binary JOINs, creating the linear chain problem.

**Compiler Simplification** (`pomagma/compiler/simplify.py`): The compiler applies algebraic simplifications like `JOIN(BOT, x) → x`, `JOIN(x, x) → x`, and commutative reordering but does not flatten associative chains. Large joins create deep expression trees that strain the simplification system.

**Torch Integration** (`pomagma/torch/corpus.py`): ObTree already supports finitary joins through `ObTree.from_join(structure, {x, y, z, ...})` using frozenset representation. The stats computation counts finitary joins as `len(args) - 1` binary operations, and the system handles extraction, compression, and language model integration for these structures.

**Cartographer Inference** (`pomagma/cartographer/infer.cpp`): Core inference algorithms like `infer_less_join_monotone` operate on binary JOIN functions, applying rules like `LESS f g → LESS JOIN(f,x) JOIN(g,x)` across all E-class combinations. These algorithms exhibit `O(N³)` complexity for N E-classes, making binary function size a critical bottleneck.

### Performance Implications

Profiling data shows that binary function operations dominate execution time, with some operations handling over 17 million calls consuming 59% of total execution time. Memory usage grows superlinearly with E-graph size due to dense binary function tables, reaching 100GB for 100K E-classes. Large finitary joins exacerbate this by creating many intermediate E-classes that exist solely to represent associative structure rather than meaningful semantic content.

## Design Overview

The long-term strategy follows an incremental approach prioritizing compatibility and performance impact:

**Phase 1: Document Current Idioms** - Systematically catalog how each component currently simulates finitary joins using existing binary JOIN machinery. This establishes baselines for performance comparison and identifies the most promising optimization targets.

**Phase 2: Incremental First-Class Support** - Implement native finitary join support in components ordered by performance impact and implementation complexity. The torch component already has partial support, making it the natural starting point, while the atlas and VM components require more extensive changes but offer the greatest performance benefits.

**Phase 3: Unified Optimization** - Once first-class support exists across components, implement cross-component optimizations like finitary join recognition in the compiler and direct atlas storage of finitary structures.

This phased approach ensures that each component can benefit from finitary joins independently while maintaining compatibility with existing code and data structures. The design avoids breaking changes by introducing finitary support alongside existing binary operations rather than replacing them wholesale.

## Detailed Design

### Terms in pomagma.reducer.syntax

**Priority: High** - The syntax layer is foundational and relatively straightforward to extend.

#### How to simulate finitary joins

Currently, large joins are created through nested binary operations. The `join_set` function in `pomagma/reducer/bohm.py` demonstrates the pattern:

```python
def join_set(terms: Collection[Term]) -> Term:
    if not terms:
        return BOT
    if len(terms) == 1:
        return next(iter(terms))
    # Filter dominated terms, then construct nested binary JOINs
    filtered_terms.sort(key=priority, reverse=True)
    result = filtered_terms[0]
    for term in filtered_terms[1:]:
        result = JOIN(term, result)
    return result
```

The `iter_join` helper function provides the inverse operation, flattening nested JOINs back into collections for analysis. This pattern works but creates `O(n)` intermediate terms for n-way joins.

#### How to add first class support

Extend the `Term` tuple structure to support variable-length argument lists for JOIN operations. Two implementation approaches are viable:

**Approach 1: Generalize Existing JOIN** - Allow `JOIN(lhs, rhs, ...)` with arbitrary argument count. This requires extending the `Term.make()` constructor and updating all pattern matching code that assumes binary structure. The advantage is seamless integration with existing code that expects JOIN terms.

**Approach 2: Introduce JOINS Operation** - Create a distinct `JOINS(frozenset(args))` operation for finitary joins while preserving binary `JOIN(lhs, rhs)` for existing code. This provides cleaner separation and easier migration but requires updating parser and pretty-printer to handle both forms.

Either approach must coordinate with the parser (`pomagma/compiler/parser.py`), simplification system (`pomagma/compiler/simplify.py`), and bridge conversion (`pomagma/reducer/bridge.py`). The parser needs syntax for expressing finitary joins, simplification needs rules for flattening and optimization, and bridge conversion needs to handle both binary and finitary forms.

Update functions that operate on JOIN terms: `is_join`, `iter_join`, `join_set`, and pattern matching throughout the reducer. The `complexity` function in `pomagma/reducer/syntax.py` needs to account for finitary join costs, and the transform system needs to handle variable-arity operations.

### ObTrees in pomagma.torch.corpus

**Priority: Low** - Already partially implemented and mostly working.

#### How to simulate finitary joins

The current `ObTree.from_join(structure, {x, y, z, ...})` method already creates finitary joins using frozenset representation:

```python
def from_join(structure: Structure, args: Collection["ObTree"]) -> "ObTree":
    if len(args) == 0:
        return ObTree(ob=structure.nullary_functions["BOT"])
    if len(args) == 1:
        return next(iter(args))
    return ObTree(name="JOIN", args=frozenset(args))
```

The stats computation correctly counts `len(args) - 1` binary operations, and the extraction system can handle frozenset arguments. This provides a model for other components.

#### How to add first class support

The existing implementation is largely complete. Minor enhancements needed:

1. **Improve extraction ordering**: The current extraction system in `pomagma/torch/extraction.py` may not handle frozenset arguments optimally. Consider deterministic ordering of frozenset elements for consistent extraction results.

2. **Language model integration**: The `Language.iadd_corpus` method in `pomagma/torch/language.py` correctly handles finitary join statistics, but weight learning could be improved by modeling finitary joins as distinct operations rather than sums of binary operations.

3. **Beta compression**: The compression system in `pomagma/torch/compression.py` should recognize finitary joins as candidates for pattern detection and abstraction.

### Atlas Storage in pomagma.atlas

**Priority: Medium** - High performance impact but requires significant implementation effort.

#### How to simulate finitary joins

Currently, finitary joins are stored as chains of binary symmetric function applications. A 1000-way join `JOIN(x[0], ..., x[999])` creates 999 intermediate E-classes and corresponding symmetric function entries. Each intermediate E-class increases memory usage and inference complexity.

#### How to add first class support

Extend the signature system to support finitary functions alongside nullary, binary, and symmetric functions. Add a new `FinitaryFunction` class with interface:

```cpp
class FinitaryFunction : noncopyable {
    std::unordered_map<std::set<Ob>, Ob> m_args_to_val;
    std::unordered_map<Ob, std::set<Ob>> m_val_to_args;
    
    public:
    Ob find(const std::set<Ob>& args) const;
    bool defined(const std::set<Ob>& args) const;
    void insert(const std::set<Ob>& args, Ob val) const;
    // Iterator support for VM operations
};
```

The storage strategy uses `std::set<Ob>` for argument sets to ensure canonical ordering and efficient comparison. Memory layout could be optimized using custom hash functions and compact representations for small sets.

Update the protobuf schema in `pomagma/atlas/structure.proto` to serialize finitary functions. The schema needs to represent variable-length argument lists and support delta compression for efficient storage.

This change requires coordinating with the VM system (`pomagma/atlas/vm.hpp`) to add finitary function opcodes and the signature system (`pomagma/atlas/signature.hpp`) to register finitary functions alongside existing function types.

### Virtual Machine Execution in pomagma.atlas.vm

**Priority: High** - Critical for performance, directly impacts surveyor and analyst execution.

#### How to simulate finitary joins

VM programs currently compile finitary join queries into nested loops over binary symmetric functions. A constraint like `LESS JOIN(x, y, z) w` generates bytecode that iterates through all possible intermediate join values, creating significant computational overhead.

#### How to add first class support

Extend the VM instruction set with finitary-specific opcodes:

- `FOR_FINITARY_FUNCTION_ARGS`: Iterate over argument sets that produce a given value
- `FOR_FINITARY_FUNCTION_VAL`: Iterate over values produced by argument sets
- `INFER_FINITARY_FUNCTION`: Assert that a set of arguments produces a value

The compiler in `pomagma/compiler/sequencer.py` and `pomagma/compiler/plans.py` needs to recognize finitary join patterns and generate appropriate opcodes. Cost models need updating to reflect the performance characteristics of finitary operations.

VM context (`pomagma/atlas/vm_impl.hpp`) must support finitary function references and argument set iteration. The execution engine needs efficient set operations and memory management for temporary argument collections.

### Cartographer Inference in pomagma.cartographer

**Priority: Medium** - Substantial performance benefits but implementation complexity.

#### How to simulate finitary joins

Current inference algorithms like `infer_less_join_monotone` apply monotonicity rules to binary JOIN functions. For finitary joins, these algorithms must iterate through all possible combinations of binary intermediate results, creating `O(N^k)` complexity for k-way joins.

#### How to add first class support

Develop direct inference algorithms for finitary joins that avoid creating intermediate E-classes. Rules like `LESS f g → LESS JOIN(f, x, y) JOIN(g, x, y)` can be implemented directly on argument sets without materializing intermediate binary joins.

The inference system needs set-based operations for argument manipulation and specialized algorithms for finitary function consistency checking. Consider parallel algorithms that process argument sets in batches to maintain performance.

### Compiler Integration in pomagma.compiler

**Priority: Medium** - Enables optimization and automatic finitary join recognition.

#### How to simulate finitary joins

The compiler currently generates nested binary JOIN expressions and relies on simplification to optimize them. Large finitary joins create deep expression trees that strain the simplification system and generate inefficient VM code.

#### How to add first class support

Extend the expression system (`pomagma/compiler/expressions.py`) to support finitary JOIN expressions. The `Expression` class needs variable-arity constructors and the parser needs syntax for finitary forms.

Add compiler phases that recognize finitary join patterns in binary expressions and convert them to finitary forms. This enables automatic optimization of existing code without requiring manual rewriting.

The simplification system (`pomagma/compiler/simplify.py`) needs rules for finitary join optimization: flattening nested structures, eliminating duplicates, and applying algebraic identities.

### Analyst Query Engine in pomagma.analyst

**Priority: Low** - Benefits from atlas and VM improvements automatically.

#### How to simulate finitary joins

The analyst compiles queries into VM programs that operate on binary functions. Finitary join queries generate complex nested loops that iterate through intermediate results, creating performance bottlenecks for large joins.

#### How to add first class support

Once the atlas and VM systems support finitary functions, the analyst automatically benefits through improved query compilation and execution. The approximation system (`pomagma/analyst/intervals.hpp`) may need updates to handle finitary function constraint propagation efficiently.

Query compilation (`pomagma/analyst/compiler.py`) should recognize finitary join patterns and generate specialized VM code that operates directly on argument sets rather than iterating through binary intermediate results.

## Implementation Risks and Mitigation

**Memory Usage**: Finitary functions could consume significant memory for argument sets. Mitigation: Use compact representations for small sets and consider argument set compression techniques.

**Compatibility**: Changes to atlas storage and VM execution could break existing code. Mitigation: Maintain backward compatibility by supporting both binary and finitary forms during transition periods.

**Complexity**: The implementation spans multiple components with different programming languages and paradigms. Mitigation: Use incremental development with extensive testing and performance benchmarking at each phase.

**Performance Regression**: Finitary implementations might perform worse than binary forms for small joins. Mitigation: Implement hybrid approaches that choose between binary and finitary forms based on argument count and performance characteristics.

## Success Metrics

- **Memory Reduction**: Measure E-class count reduction for large finitary joins
- **Execution Speed**: Benchmark VM execution time for finitary join queries
- **Inference Efficiency**: Profile cartographer inference performance on finitary join workloads
- **Compatibility**: Ensure all existing tests pass with finitary support enabled

The finitary join enhancement represents a significant optimization opportunity that could substantially improve Pomagma's performance for large disjunctive expressions while maintaining the system's mathematical foundations and compatibility with existing code. 