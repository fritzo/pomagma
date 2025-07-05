# Design Doc: A Guide to Pomagma's Syntax Representations

## Overview

Pomagma employs multiple syntax representations across its different modules, each optimized for specific performance and functionality constraints. This document provides a comprehensive analysis of these representations, their design trade-offs, applications, and recommendations for future consolidation and enhancement.

The primary representations include `Expression` which provides rich APIs for compiler operations, `Term` which offers minimal overhead for functional programming, `ObTree` which bridges symbolic and semantic analysis for machine learning, and the C++ `Corpus Term` which delivers high-performance validation capabilities. Additional specialized representations handle graphs, approximations, and virtual machine execution.

## Core Syntax Representations

### 1. Expression (`pomagma.compiler.expressions`)

Expression serves as the high-level syntax representation for the compiler frontend and query processing. It employs a hash-consed immutable structure using `HashConsArgsMeta` for efficient deduplication, with Polish notation as its canonical string representation. The design emphasizes lazy property computation for variables, constants, terms, and transformations, supported by a rich type system with signature-based arity checking. Core operations include substitution, replacement, variable swapping, and symbol permutation.

Expression finds primary application in compiler frontend tasks including parsing, type checking, and transformation. It drives query compilation for building inference rules and constraint satisfaction, supports program synthesis through sketching and hole-filling algorithms, and enables simplification through canonical form reduction and optimization.

The representation excels in performance through hash-consing and string interning, providing a rich API for symbolic manipulation with strong type safety through signature validation and efficient equality operations. However, it carries high memory overhead for simple expressions, remains limited to Python environments without C++ interoperability, and provides only basic support for variable binding beyond simple substitution.

### 2. Term (`pomagma.reducer.syntax`)

Term provides a functional representation optimized for lambda calculus reduction and combinatory logic operations. Built on a tuple-based immutable structure that supports efficient pattern matching, it uses de Bruijn indices for variable binding through `IVAR` and `NVAR` constructs. The design includes quotation support for reflection and metaprogramming, an extensible transform system for recursive tree transformations, and dual parsing support for both Polish notation and S-expressions. Built-in complexity analysis uses configurable atom costs for performance evaluation.

The representation drives lambda calculus reduction including beta reduction, normalization, and evaluation processes. It supports various combinator calculi including SK, BICS, and other systems, enables program transformation through abstract interpretation and code generation, and facilitates sugar compilation from domain-specific languages to combinator targets.

Term achieves minimal memory footprint with efficient pattern matching capabilities and supports both nominal and de Bruijn variable representations through its extensible transform system. However, the tuple-based design offers limited type safety where malformed structures are possible, lacks automatic deduplication mechanisms, and requires manual memory management of term structures.

### 3. ObTree (`pomagma.torch.corpus`)

ObTree provides a hybrid representation that bridges raw syntax trees and E-graph equivalence classes. Its partially quotiented structure uses E-class leaves to represent fully reduced subterms while maintaining symbolic structure for unresolved expressions. The design supports lazy evaluation from Expression inputs to E-class resolution, handles finitary joins through frozenset representation, and includes comprehensive statistics computation for corpus analysis. Deep PyTorch integration enables tensor materialization for machine learning workflows.

Primary applications include corpus analysis for computing statistics over expression collections, language model training through PCFG parameter estimation, expression complexity analysis using probability-based cost metrics, and beta compression for pattern-based code optimization.

ObTree achieves efficient hybrid representation with seamless Expression integration and rich statistics capabilities that integrate naturally with PyTorch tensor operations. However, the dual semantics between syntax trees and E-class quotients create conceptual complexity, the implementation remains limited to PyTorch ecosystems, and users may experience confusion when navigating between symbolic and quotient views of the same data.

### 4. Corpus Term (`pomagma.analyst.corpus` - C++)

Corpus Term delivers a high-performance C++ representation optimized for corpus validation and analysis operations. The design uses enum-based arity classification for efficient dispatch, implements shared sub-expression storage through pointer sharing for memory efficiency, and provides direct E-class resolution for grounding symbolic terms against E-graph structures. Integration with approximation systems enables interval analysis, while built-in histogram computation supports language modeling workflows.

Core applications center on corpus validation for checking expression validity against E-graphs, language fitting to learn grammar weights from corpus statistics, approximation-based interval constraint propagation, and dependency analysis for computing expression relationships.

The C++ implementation provides high performance with efficient memory sharing, direct E-graph integration, and robust parallel processing support. However, the design remains constrained to C++ ecosystems, requires manual memory management, and offers less flexibility than Python-based alternatives for rapid prototyping and experimentation.

## Secondary Representations

Beyond the primary syntax representations, Pomagma employs several specialized structures for specific computational domains. The **Graphs Term** (`pomagma.reducer.graphs`) provides integer-based sharing for efficient graph representation with topological operations, primarily supporting graph reduction algorithms, sharing analysis, and optimal evaluation strategies.

**Approximation Structures** (`pomagma.analyst.approximate`) implement interval-based approximation using dense set representations with bit vectors and interval propagation for constraint solving. These support parallel work-stealing for expensive computations and find application in constraint satisfaction, interval analysis, and lazy validation workflows.

**Virtual Machine Context** (`pomagma.atlas.macro.vm`) serves as the runtime representation for virtual machine execution, using fixed-size arrays for E-class identifiers, set references for efficient iteration, and parallelization state for work distribution across virtual machine execution, parallel inference, and E-graph manipulation tasks.

## Comparative Analysis

### Performance Characteristics

| Representation | Memory Usage | Construction Cost | Transformation Cost | Equality Check |
|---------------|--------------|-------------------|---------------------|----------------|
| Expression    | High         | High (hash-cons)  | Medium              | O(1)           |
| Term          | Low          | Low               | Low                 | O(n)           |
| ObTree        | Medium       | Medium            | Medium              | O(1)           |
| Corpus Term   | Low          | Low               | Low                 | O(n)           |

### Functionality Matrix

| Feature                | Expression | Term | ObTree | Corpus Term |
|---------------------- |------------|------|--------|-------------|
| Hash-consing          | ✓          | ✗    | ✓      | ✗           |
| Type safety           | ✓          | ✗    | ✓      | ✓           |
| Variable binding      | ✓          | ✓    | ✗      | ✓           |
| E-class resolution    | ✗          | ✗    | ✓      | ✓           |
| Pattern matching      | ✗          | ✓    | ✗      | ✓           |
| Transformation system | ✓          | ✓    | ✗      | ✗           |
| Statistics            | ✗          | ✓    | ✓      | ✓           |
| PyTorch integration   | ✗          | ✗    | ✓      | ✗           |
| C++ interoperability | ✗          | ✗    | ✗      | ✓           |

### Design Philosophy Comparison

Expression prioritizes correctness and developer ergonomics through strong typing, immutability, and rich APIs, making it suitable for high-level symbolic manipulation where correctness trumps raw performance. Term emphasizes minimal representation and flexibility for functional programming patterns, ideal for algorithms requiring direct control over data structures and memory usage.

ObTree bridges symbolic and semantic representations for machine learning applications, providing hybrid capabilities at the cost of increased conceptual complexity. Corpus Term optimizes specifically for high-performance server applications with direct E-graph integration, deliberately sacrificing flexibility for maximum computational efficiency.

## Usage Patterns and Applications

The compiler pipeline flows from source code through Expression-based parsing and simplification to query compilation and virtual machine program generation. Expression provides the rich API and type safety essential for frontend operations, with parsed expressions undergoing simplification before compilation to executable programs.

The reducer pipeline processes syntax through Term-based reduction and normalization workflows. Term's minimal overhead and direct lambda calculus support enable efficient combinator rule application and canonical form reduction for functional programming tasks.

PyTorch integration leverages ObTree to bridge symbolic expressions with E-graph statistics for machine learning workflows. ObTree enables differentiable computation over symbolic structures by connecting Expression inputs to statistical tensor operations through corpus analysis.

The analyst pipeline processes string inputs through C++ Term structures for high-performance validation and constraint satisfaction. The C++ implementation maximizes performance for corpus validation and approximation-based analysis tasks requiring intensive computational processing.

## Interoperability and Conversion

Current conversion patterns rely heavily on string intermediaries for cross-representation communication. Expression integrates with string parsing through `parse_string_to_expr()` and string serialization, while ObTree connects to Expression via `ObTree.from_expr()` and back through `Extractor.extract_from_obtree()`. Term supports both Polish notation through `polish_parse()` and `polish_print()`, and the C++ Corpus Term uses dedicated parser infrastructure for string processing.

Significant conversion gaps exist between representations, particularly the lack of direct Expression-Term conversion which forces expensive string round-trips. Similarly, Term and ObTree lack direct conversion paths, and the C++/Python boundary limits Corpus Term integration with Python-based representations, creating performance bottlenecks and development friction.

## Future Improvements

- [ ] **Standardize on Polish notation** - Remove S-expression support from `pomagma.reducer.syntax` and `pomagma.reducer.graphs`, eliminate `sexpr_parse()` and `sexpr_print()` functions in favor of consistent Polish notation across all representations

- [ ] **Consolidate graphs.Term into syntax.Term** - Merge `pomagma.reducer.graphs.Term` functionality into the main `pomagma.reducer.syntax.Term`, eliminating the specialized integer-based representation while preserving graph operation capabilities

- [ ] **Implement direct Expression↔Term conversion** - Add `Expression.to_term()` and `Term.to_expression()` methods to eliminate expensive string round-trips, benefiting the compiler-reducer integration and program synthesis workflows

- [ ] **Create PyTorch bridge for analyst** - Extend `pomagma.torch.corpus` to interface with C++ `Corpus Term` structures, enabling PyTorch-based analysis of high-performance corpus validation results for machine learning applications

- [ ] **Unify corpus statistics interfaces** - Implement common `CorpusStats` protocol across Expression, Term, ObTree, and Corpus Term to standardize histogram computation and language model training workflows

- [ ] **Add C++ Expression bindings** - Create pybind11 wrappers for Expression to enable direct use in analyst and cartographer systems, eliminating string conversion overhead in high-performance validation and approximation tasks

- [ ] **Implement lazy hash-consing for Term** - Add optional hash-consing to `Term.make()` through a registry parameter, providing Expression-like deduplication benefits for memory-intensive reducer applications when needed

- [ ] **Consolidate C++ Term representations** - Evaluate merging `pomagma.analyst.corpus.Term` with other C++ term structures in approximation and virtual machine contexts to reduce maintenance overhead and improve type consistency 
