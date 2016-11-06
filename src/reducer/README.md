# Reduction Engines

This Reducer module implements various interpreters for nondeterministic
extensional combinatory algebra, henceforth SKJ/H&ast;.
The algorithms extend the beta-eta reduction (aka strong normalization) algorithm of Boulifa and Mezohiche
<a href="#user-content-Boulifa03">[Boulifa03]</a>
to nondeterministic combinatory algebra.

## Lineage of the various engines

- [`engine.py`](./engine.py)
  An initial implementation of a combinator reduction machine supporting many
  different reduction rules.
  <br> Supports: ['sk', 'join', 'quote', 'types', 'lib', 'unit']

- [`engine.hpp`](./engine.hpp)
  A C++ port of an early version of engine.py. This is very limited, and mostly
  exercises serialization plumbing.

- [`trace.py`](./trace.py)
  A simple deterministic engine with tracing support.
  <br> Supports: ['sk', 'quote', 'lib']

- [`continuation.py`](./continuation.py)
  Forked from engine.py, this starts to use Bohm-trees = continuations as the
  basic data structure during evaluation, simplifying nondeterminism.
  <br> Supports: ['sk', 'join', 'quote', 'lib']

- [`de_bruijn.py`](./de_bruijn.py)
  Forked from continuation.py, this uses de Bruijn variables rather than
  nominal variables for &lambda; binding. This simplifies the logic of
  `try_decide_less` by avoiding the need to &alpha;-convert.
  <br> Supports: ['sk', 'join', 'quote', 'lib']

- [`learn.py`](./learn.py)
  Forked from de_bruijn.py, this aims to implement reduction step learning.
  The goal is to provide native support for definable types, using the
  recursive definition of `A`.
  <br> Supports: ['sk', 'join']

## References

- [Scott76] <a name="Scott76"/>
  Dana Scott (1976)
  [Datatypes as Lattices](http://www.cs.ox.ac.uk/files/3287/PRG05.pdf)
- [Hindley08] <a name="Hindley2008"/>
  J. Roger Hindley, J.P. Seldin (2008)
  "Lambda calculus and combinatory logic: an introduction"
- [Koopman91] <a name="Koopman91"/>
  Philip Koopman, Peter Lee (1991)
  [Architectural considerations for graph reduction](http://users.ece.cmu.edu/~koopman/tigre/lee_book_ch15.pdf)
- [Boulifa03] <a name="Boulifa03"/>
  Rabea Boulifa, Mohamed Mezghiche (2003)
  [Another Implementation Technique for Functional Languages](http://jfla.inria.fr/2003/actes/PS/04-boulifa.ps)
- [Obermeyer09] <a name="Obermeyer09"/>
  Fritz Obermeyer (2009)
  [Automated Equational Reasoning in Nondeterministic &lambda;-Calculi Modulo Theories H*](http://fritzo.org/thesis.pdf)
- [Fischer11] <a name="Fischer11"/>
  Sebastian Fischer, Oleg Kiselyov, Chung-Chieh Shan (2011)
  [Purely functional lazy nondeterministic programming](http://okmij.org/ftp/Haskell/FLP/lazy-nondet.pdf)
