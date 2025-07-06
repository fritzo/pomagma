# Reduction Engines

This module implements virtual machines for nondeterministic
extensional combinatory algebra and &lambda;-calculus.

## Engineering strategy

tl;dr
- nondeterminism + order oracle = types
- order oracle + reflection = a very strong foundation

The engineering strategy has been to get "types for free" by adding angelic
nondeterminism to the language and implementing a theorem prover to weakly
decide Scott ordering and to "garbage collect" concurrent continuations that
are provably redundant.  This theorem prover is limited, but approaches the
Pi02 complete theory H&ast;.  Since we've put so much effort into this theorem
prover, we put more effort into exposing the theorem prover through
reflection.  Reflection has to be very careful and work always through a
quoting comonad that flattens out order.  Once we have the order oracle and
reflection, this system is very strong, capable of expressing the full
arithmetic hierarchy.

## Submodules

### Core Reduction Engines

- **`bohm.py`** - Main linear Böhm tree reduction engine with eager evaluation, beta reduction, abstraction, and Scott ordering decision procedures. Implements the primary reduction algorithm used throughout Pomagma.
- **`curry.py`** - Alternative combinatory logic reduction engine using pure I,K,B,C,S combinators. Simpler but less powerful than the Böhm engine.

### Syntax and Data Structures  

- **`syntax.py`** - Core `Term` data structure with support for parsing/printing in Polish notation and S-expressions. Provides the fundamental representation for all terms.
- **`graphs.py`** - Rational term graphs with sharing for efficient representation of cyclic and repeated structures. Used for graph reduction algorithms and optimal evaluation.
- **`lib.py`** - Standard library of typed combinators including booleans, products, sums, numerals, lists, and streams. Provides the foundation for practical programming.

### Language Integration

- **`sugar.py`** - Domain-specific language for readable term construction using lambda-let notation and the `@combinator` decorator. Makes writing terms much more ergonomic.
- **`bridge.py`** - Conversion bridge between compiler `Expression` objects and reducer `Term` objects. Critical for integration with the PyTorch frontend.
- **`data.py`** - Encoding/decoding between Python data structures and terms, enabling practical I/O and interfacing with external systems.

### Specialized Systems

- **`systems.py`** - Framework for step-by-step reduction of mutually recursive combinator systems. Used for interactive exploration and debugging.
- **`programs.py`** - Python wrapper for typed SKJ programs with automatic encoding/decoding. Provides a clean interface for calling reducer functions from Python.

### Research Implementations

- **`huet98.py`** - Implementation of Gerard Huet's regular Böhm trees with decision procedures for extensional equality. Research prototype for comparison.
- **`koopman.py`** - Combinator graph reduction following Philip Koopman's architecture. Alternative evaluation strategy research.
- **`church.py`** - Nominal lambda calculus with automatic variable management. Used in some examples for pedagogical purposes.

### Utilities

- **`util.py`** - Core utilities including logging, profiling, three-valued logic operations, and stack manipulation. Used throughout the module.
- **`pattern.py`** - Pattern matching utility for destructuring terms with nominal variables. Used by the data encoding system.
- **`linker.py`** - Links free variables to library definitions (e.g., `lib.true` → `lib.true`). Used in command-line interface and testing.
- **`testing.py`** - Test utilities including property-based testing strategies and test case iteration. Internal development support.

## References

- [Scott76] <a name="Scott76"/>
  Dana Scott (1976)
  [Datatypes as Lattices](http://www.cs.ox.ac.uk/files/3287/PRG05.pdf)
- [Obermeyer09] <a name="Obermeyer09"/>
  Fritz Obermeyer (2009)
  [Automated Equational Reasoning in Nondeterministic &lambda;-Calculi Modulo Theories H*](http://fritzo.org/thesis.pdf)
- [Huet98] Gerard Huet (1998)
  [Regular Bohm Trees](http://pauillac.inria.fr/~huet/PUBLIC/RBT2.pdf)
- [Feferman05] <a name="Feferman05"/>
  Solomon Feferman (2005)
  [Predicativity](http://math.stanford.edu/~feferman/papers/predicativity.pdf)
- [Fischer11] <a name="Fischer11"/>
  Sebastian Fischer, Oleg Kiselyov, Chung-Chieh Shan (2011)
  [Purely functional lazy nondeterministic programming](http://okmij.org/ftp/Haskell/FLP/lazy-nondet.pdf)
