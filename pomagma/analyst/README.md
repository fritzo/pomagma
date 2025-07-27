# Analyst: Query Engine for E-graphs

The analyst provides constraint satisfaction and validation services over read-only equality graphs (E-graphs) in ordered combinatory algebras. It compiles declarative queries into efficient constraint propagation algorithms using 16-bit E-class identifiers (macro atlas).

## Purpose

The analyst serves as Pomagma's query engine, answering targeted questions about E-graph structures through approximation and constraint propagation. It operates over pre-built E-graphs without modification, supporting theorem proving, program synthesis, and symbolic constraint solving through a client-server architecture.

## Core Algorithms

### Constraint Satisfaction via Virtual Machine Programs

The `solve` operation compiles logical constraints into virtual machine bytecode that executes over E-graph structures. Given an expression with free variables and a theory, it returns:

- **Necessary solutions**: values that must satisfy all constraints  
- **Possible solutions**: values that could satisfy constraints but are not provably necessary

The `compile_solver` function transforms constraint specifications into VM programs through sequent-based optimization, using specialized opcodes for E-graph traversal and temporary fact assertion.

### Approximation with Upper and Lower Bounds

Each `Approximation` represents partial knowledge about E-classes:

- `upper`: E-classes that could contain the true value
- `lower`: E-classes that definitely do not contain the true value
- `ob`: specific E-class if exactly determined

Operations preserve soundness through monotonic refinement. The system uses three-valued logic (`TRUE`/`FALSE`/`MAYBE`) for reasoning under incomplete information.

### Interval-Based Constraint Propagation

The intervals subsystem implements lazy constraint propagation using four boundary sets per approximation:

- `ABOVE`/`BELOW`: positive ordering constraints
- `NABOVE`/`NBELOW`: negative ordering constraints  

The `lazy_validate` algorithm refines interval bounds through iterative propagation until convergence. Expensive computations are cached using fingerprinted dense sets with parallel work-stealing.

### Expression Simplification

The simplifier applies confluent rewrite rules guided by probabilistic routing tables. Simplification reduces expressions to canonical forms, often enabling more efficient subsequent constraint satisfaction.

### Corpus Validation

The validator processes expression collections through dependency analysis, memoized computation, and parallel evaluation. The `fit_language` operation learns probabilistic grammar weights that maximize corpus likelihood.

## Data Structures

### Approximation Objects
```cpp
struct Approximation {
    Ob ob;           // 16-bit E-class identifier
    DenseSet upper;  // possible values (bit vector)
    DenseSet lower;  // impossible values (bit vector)
};
```

### Virtual Machine Context
```cpp
struct Context {
    Ob obs[256];                        // 16-bit E-class identifiers
    const DenseSet::RawData* sets[256]; // set references for iteration
    size_t block;                       // parallelization state
};
```

### Interval Approximations
```cpp
struct Approximation {
    SetId bounds[4];  // ABOVE, BELOW, NABOVE, NBELOW constraint boundaries
};
```

### Corpus Terms
```cpp
struct Term {
    Arity arity;              // function type classification
    std::string name;         // symbol name
    const Term* arg0, *arg1;  // shared sub-expressions
    Ob ob;                    // resolved E-class reference
};
```

## Architecture Integration

The analyst loads pre-built E-graphs from cartographer batch inference or surveyor forward-chaining and operates read-only over these structures. Query execution uses temporary relations (`RETURN`/`NRETURN`) without modifying the underlying E-graph.

The compiler generates VM programs for analyst execution. The theorist uses analyst validation to guide conjecture formation. Query compilation applies optimization techniques from static theory compilation but operates under interactive latency constraints. 