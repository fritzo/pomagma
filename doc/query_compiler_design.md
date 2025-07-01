# Design Doc: Query Compiler for Forward-Chaining Inference

## Objective

Compile a concise, flexible logic programming language down to efficient optimized inference plans that perform forward-chaining reasoning over equality graphs (E-graphs). The system transforms high-level declarative inference rules into low-level virtual machine programs that efficiently explore the space of equational and relational facts in ordered combinatory algebras.

## Background

### Logic Programming and Forward Chaining
Logic programming languages like Prolog use backward chaining to prove goals by recursively reducing them to subgoals. Pomagma instead employs **forward chaining**, systematically deriving new facts from existing ones using inference rules until saturation is reached. This approach excels at building comprehensive databases of derived facts, which can then answer queries efficiently through simple lookup rather than expensive search.

### Relational Databases and Query Optimization
Relational database systems face similar challenges in translating high-level declarative queries (SQL) into efficient execution plans. Database query optimizers use cost-based analysis to choose among alternative join orders, access methods, and algorithms. Pomagma's compiler applies analogous techniques to logic programming, optimizing the order of operations in inference rules to minimize computational cost while preserving logical completeness.

### E-graphs and Congruence Closure
An **equality graph (E-graph)** is a data structure from automated reasoning that compactly represents equivalence classes of terms under some equational theory. E-graphs support efficient **congruence closure**—the process of propagating equality through function applications. Pomagma extends this concept to handle not just equality but also ordering relations (`LESS`, `NLESS`) in ordered combinatory algebras, enabling reasoning about both definitional and approximation relationships.

### Term Rewriting and Confluence
Term rewriting systems use directed equations (rules) to transform terms by repeatedly applying pattern-matching substitutions. Pomagma's inference rules can be viewed as conditional rewrite rules where antecedents serve as side conditions. The forward-chaining process systematically applies these rules until a **confluent** state is reached where no new facts can be derived.

### Abstract Interpretation and Domain Theory
In abstract interpretation, program properties are computed by executing programs over abstract domains that safely approximate concrete values. Pomagma's ordered combinatory algebras embody this principle: the Scott ordering `x ⊑ y` means "x approximates y," and inference rules preserve this approximation relationship, enabling sound reasoning about program properties through symbolic execution.

### Probabilistic Programming and Bayesian Inference
Modern probabilistic programming systems must efficiently explore large spaces of possible executions. Pomagma's cost-based optimization mirrors techniques from probabilistic inference, where the goal is to focus computational resources on the most promising regions of the search space, guided by probability estimates and relevance measures.

## Design Overview

The query compilation system transforms declarative inference rules into optimized virtual machine programs through a multi-stage pipeline. **Theory files** (`.theory`) contain facts and rules in a logic programming language with ASCII-art inference rule syntax. The **parser** converts these into normalized sequents, which the **optimizing compiler** transforms into execution plans using cost-based heuristics. The **code generator** translates plans into assembly-like virtual machine programs that execute efficiently over E-graph data structures. The **virtual machine** provides specialized opcodes for iterating over relations and functions, with automatic parallelization and set operations for scalable performance.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Theory Files  │───▶│     Parser      │───▶│   Normalizer    │
│   (.theory)     │    │                 │    │   (Sequents)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  VM Programs    │◀───│ Code Generator  │◀───│ Query Optimizer │
│   (.programs)   │    │   (Frontend)    │    │   (Compiler)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   E-graph VM    │◀───│     Agenda      │◀───│  Runtime Solver │
│  (Execution)    │    │ (Dispatch Table)│    │  (Analyst API)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Design Details

### Logic Programming Language

Pomagma's logic programming language provides a declarative syntax for expressing inference rules over ordered combinatory algebras. The language supports **facts** (ground statements) and **rules** (conditional inference patterns) using a distinctive ASCII-art syntax that visually separates premises from conclusions.

**Facts** are atomic statements written in Polish notation:
```
CLOSED I
CLOSED K  
CLOSED S
EQUAL I APP APP S K K
LESS BOT x
LESS x TOP
```

**Rules** use horizontal bars to separate antecedents (above) from succedents (below):
```
CLOSED x   CLOSED y
-------------------
  CLOSED APP x y

LESS x y   LESS y z
-------------------
     LESS x z
```

The language supports several relation and function types from universal algebra:
- **Unary relations**: `CLOSED x`, `NCLOSED x` (predicates on terms)
- **Binary relations**: `LESS x y`, `NLESS x y`, `EQUAL x y` (relationships between terms)  
- **Nullary functions**: Constants like `I`, `K`, `S`, `BOT`, `TOP`
- **Injective functions**: One-to-one mappings (not shown in examples)
- **Binary functions**: `APP x y` (function application), `COMP x y` (composition)
- **Symmetric functions**: `JOIN x y` (commutative operations)

Variables are lowercase identifiers (`x`, `y`, `z`) that can be bound and quantified across rules. The parser automatically infers types and arities based on usage patterns, enabling concise expression of complex logical relationships.

**Normalization** transforms rules into a canonical form where each conclusion has at most one succedent, variables are properly scoped, and compound expressions are decomposed into atomic predicates. This process may generate multiple normalized rules from a single source rule when disjunctive conclusions are involved.

### Virtual Machine Architecture

The virtual machine executes specialized bytecode programs over E-graph data structures, providing efficient primitives for the common operations in forward-chaining inference. The VM is designed around the observation that most inference involves systematic iteration over sets of objects and relationships, combined with conditional testing and fact insertion.

**Execution Model**: Programs are sequences of opcodes that manipulate a context containing:
- `obs[256]`: Array of object identifiers (E-class IDs)
- `sets[256]`: Array of set references for efficient iteration
- `block`: Current parallelization block (for `FOR_BLOCK`/`IF_BLOCK`)

**Core Instruction Types**:

*Iteration Opcodes* systematically enumerate elements:
```assembly
FOR_ALL x                    # iterate over all objects
FOR_UNARY_RELATION REL x     # iterate over REL(x)  
FOR_BINARY_RELATION_LHS REL x y  # iterate y where REL(x,y)
FOR_BINARY_FUNCTION_LHS FUN x y z # iterate y,z where FUN(x,y)=z
```

*Set Operations* optimize complex iteration patterns:
```assembly  
LETS_UNARY_RELATION REL set      # set := domain(REL)
LETS_BINARY_RELATION_LHS REL x set # set := {y : REL(x,y)}
FOR_POS_POS x set1 set2          # iterate x ∈ set1 ∩ set2
FOR_POS_NEG x set1 set2          # iterate x ∈ set1 \ set2
```

*Conditional Testing* enables efficient filtering:
```assembly
IF_EQUAL x y             # continue if x = y
IF_UNARY_RELATION REL x  # continue if REL(x)
IF_BINARY_RELATION REL x y # continue if REL(x,y)
```

*Fact Assertion* updates the E-graph:
```assembly
INFER_EQUAL x y               # assert x = y (triggers congruence closure)
INFER_UNARY_RELATION REL x    # assert REL(x)
INFER_BINARY_FUNCTION FUN x y z # assert FUN(x,y) = z
```

*Variable Binding* manages local scope:
```assembly
LET_BINARY_FUNCTION FUN x y z  # z := FUN(x,y), fail if undefined
FOR_INJECTIVE_FUNCTION_KEY FUN x y # y := FUN(x), iterate if defined
```

*Parallelization Support* enables scalable execution:
```assembly
FOR_BLOCK                # begin parallel region
IF_BLOCK x               # continue if x belongs to current worker block
```

The VM uses an **event-driven dispatch model** where programs are triggered by changes to specific relations or functions. The `Agenda` class maintains mapping from database events (e.g., insertion into `LESS`) to relevant program fragments, enabling incremental execution as new facts are derived.

### Optimizing Compiler

The query optimizer transforms normalized sequents into efficient execution plans using cost-based heuristics. The optimization process balances logical correctness with computational efficiency, similar to database query optimization but adapted for the distinctive patterns of forward-chaining inference.

**Plan Representation**: The compiler builds execution plans as trees of operation nodes:
- `Iter(var, body)`: Iterate variable over some domain
- `Test(expr, body)`: Conditional execution based on predicate  
- `Let(expr, body)`: Variable binding from function evaluation
- `Ensure(expr)`: Assert a fact into the database

**Optimization Algorithm** (`optimize_plan`) uses a greedy strategy with backtracking:

1. **Base Cases**: If all variables are bound and no antecedents remain, generate an `Ensure` operation.

2. **Eager Testing**: Process relational tests as early as possible when their variables are bound:
   ```python
   if a.is_rel() and a.vars <= bound:
       return Test.make(a, optimize_plan(remaining_antecedents, succedent, bound))
   ```

3. **Eager Binding**: Bind variables through function evaluation when arguments are available:
   ```python
   if a.is_fun() and a.vars <= bound and a.var not in bound:
       return Let.make(a, optimize_plan(remaining_antecedents, succedent, bound | {a.var}))
   ```

4. **Strategic Iteration**: Choose iteration variables to minimize search space:
   - **Forward iteration**: Variables appearing in antecedents
   - **Backward iteration**: Variables appearing in function inverses  
   - **Unknown iteration**: Variables in succedents (for negative constraints)

**Cost Model**: Each plan node estimates its computational cost:
- `Iter` cost scales with domain size (estimated as `OBJECT_COUNT`)
- `Test` cost includes filtering probability (e.g., `NLESS` has 90% filter rate)
- `Let` cost accounts for function evaluation overhead
- Nested operations multiply costs, encouraging efficient nesting orders

**Specialized Iteration Patterns**:
- `IterInvInjective`: Iterate inverse of injective function (unique preimage)
- `IterInvBinary`: Iterate all preimages of binary function value
- `IterInvBinaryRange`: Iterate one argument given the other and result

The compiler generates multiple alternative plans and selects the minimum-cost option, enabling automatic adaptation to different data distributions and query patterns.

### Code Generation

The frontend (`pomagma/compiler/frontend.py`) translates optimized execution plans into virtual machine bytecode. This phase handles the mechanical details of register allocation, instruction selection, and control flow generation while preserving the logical structure determined by the optimizer.

**Program Structure**: Generated programs follow a template-based approach:
```assembly
# plan X: cost = Y.Z  
# using [source rule]
# infer [derived conclusion]
FOR_NULLARY_FUNCTION I I_     # bind constants
FOR_UNARY_RELATION CLOSED x   # iterate over domain
IF_BINARY_RELATION LESS x y   # test conditions  
INFER_EQUAL x y               # assert conclusion
```

**Register Allocation**: Variables are mapped to the `obs[]` and `sets[]` arrays using simple linear allocation. The system supports up to 256 variables per program, which suffices for the complexity of typical inference rules.

**Set Optimization**: The frontend recognizes common iteration patterns and generates efficient set operations:
- Multiple tests on the same variable become intersection operations (`FOR_POS_POS`)
- Negative tests become set difference operations (`FOR_POS_NEG`)  
- Complex filtering patterns use precomputed sets (`LETS_BINARY_RELATION_LHS`)

**Parallelization**: Rules with high computational cost (threshold `MIN_SPLIT_COST = 1.5`) are automatically parallelized using `FOR_BLOCK`/`IF_BLOCK` constructs. The VM runtime distributes work across multiple threads by partitioning the object space.

**Event-Driven Compilation**: Programs are categorized by their trigger events:
- `GIVEN_EXISTS`: Programs triggered by any object creation
- `GIVEN_UNARY_RELATION`: Programs triggered by unary relation insertion
- `GIVEN_BINARY_FUNCTION`: Programs triggered by binary function definition
- General cleanup programs run periodically to handle complex multi-event rules

### Static Theory Compilation

Pomagma ships with precompiled inference programs for standard theories of combinatory logic, lambda calculus, and abstract interpretation. These static programs (`.programs` files) are generated offline from theory files (`.theory`) and optimized for the specific structure of each domain.

**Example Theory: SK Combinatory Logic**
The `sk.theory` file defines the standard S and K combinators:
```
EQUAL APP I x x
EQUAL APP APP K x y x  
EQUAL APP APP APP S x y z APP APP x z APP y z
```

The compiler generates 46 optimized programs totaling ~2300 lines of VM code. Representative examples:

*Constant Definition*:
```assembly
# plan 9: cost = 1.0
# using |- EQUAL APP I x x
FOR_NULLARY_FUNCTION I I_
FOR_ALL x
INFER_BINARY_FUNCTION APP I_ x x
```

*Complex Combinator Rule*:
```assembly  
# plan 33: cost = 2.2
# using |- EQUAL APP APP APP S x y z APP APP x z APP y z
FOR_NULLARY_FUNCTION S S_
FOR_BINARY_FUNCTION_LHS APP S_ x APP_S_x
FOR_BINARY_FUNCTION_LHS APP APP_S_x y APP_APP_S_x_y
LETS_BINARY_FUNCTION_LHS APP x APP_x_z
LETS_BINARY_FUNCTION_LHS APP y APP_y_z  
FOR_POS_POS z APP_x_z APP_y_z
LET_BINARY_FUNCTION APP x z APP_x_z
LET_BINARY_FUNCTION APP y z APP_y_z
INFER_BINARY_BINARY APP APP_APP_S_x_y z APP APP_x_z APP_y_z
```

**Performance Characteristics**: Static compilation enables several optimizations:
- **Specialization**: Rules are optimized for known symbol arities and properties
- **Inlining**: Common patterns are pre-expanded to avoid runtime dispatch
- **Ordering**: Rule application sequences are optimized for typical forward-chaining patterns
- **Parallelization**: Expensive rules are automatically parallelized based on cost analysis

### Runtime Query Interface

The analyst API (`pomagma/analyst/compiler.py`) provides runtime compilation for user queries and dynamic theory extensions. This interface allows interactive exploration and theorem proving without requiring full system recompilation.

**Solver Generation**: The `compile_solver` function produces specialized programs for constraint satisfaction:
```python
def compile_solver(expr, theory):
    """
    Produces a set of programs that finds values of term satisfying a theory.
    Inputs:
        expr - string, an expression with free variables
        theory - string representing a theory (in .theory format)  
    Outputs:
        a program to be consumed by the virtual machine
    """
```

Example usage:
```python
expr = 's'
theory = """
    LESS APP V s s       NLESS x BOT      NLESS x I
    LESS APP s BOT BOT   --------------   ----------------  
    EQUAL APP s I I      LESS I APP s x   LESS TOP APP s x
    LESS TOP APP s TOP
"""
program = compile_solver(expr, theory)
```

**Query Types**: The system supports two complementary inference modes:
- **Necessary inference**: Find values that must satisfy all constraints
- **Possible inference**: Find values that could satisfy constraints (existential)

**Runtime Optimization**: Dynamic compilation applies the same optimization techniques as static compilation but must complete quickly enough for interactive use. The system balances compilation time against execution efficiency, using simpler heuristics when full optimization would be too expensive.

**Integration with Analyst**: The runtime compiler integrates with Pomagma's broader analyst infrastructure, enabling seamless combination of precompiled theories with user-specified constraints. This supports applications ranging from interactive theorem proving to automated program synthesis.

### Implementation Considerations

**Performance**: The virtual machine achieves high performance through several design choices:
- **Specialized opcodes** eliminate interpretation overhead for common operations
- **Dense set representations** use bit vectors for efficient iteration and set operations  
- **Event-driven execution** avoids redundant work by triggering only relevant rules
- **Automatic parallelization** scales to multi-core systems without user intervention

**Memory Management**: The system uses persistent data structures where possible, minimizing copying overhead during inference. The E-graph representation shares structure between equivalent terms, and the VM context reuses buffers across multiple program executions.

**Debugging Support**: Generated programs include extensive comments linking back to source rules and optimization decisions. The VM supports tracing modes that log all executed operations, enabling analysis of performance bottlenecks and logical errors.

**Extensibility**: The modular design allows easy addition of new opcodes, optimization passes, and language constructs. The parser and compiler use table-driven approaches that can be extended without modifying core algorithms.

This design enables Pomagma to efficiently bridge the gap between high-level logical specifications and low-level computational execution, supporting both large-scale automated reasoning and interactive theorem development. 