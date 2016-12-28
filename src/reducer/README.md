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

## Lineage of the various engines

- [`engine.py`](./engines/engine.py)
  An initial implementation of a combinator reduction machine supporting many
  different reduction rules.
  This is algorithm is based on combinatory beta-eta reduction
  (aka strong normalization) of Boulifa and Mezohiche
  <a href="#user-content-Boulifa03">[Boulifa03]</a>,
  and extends it to nondeterministic combinatory algebra.

- [`bohm.py`](./bohm.py)
  Forked from continuation.py, this uses de Bruijn variables rather than
  nominal variables for &lambda; binding. This simplifies the logic of
  `try_decide_less` by avoiding the need to &alpha;-convert.

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
- [Feferman05] <a name="Feferman05"/>
  Solomon Feferman (2005)
  [Predicativity](http://math.stanford.edu/~feferman/papers/predicativity.pdf)
- [Fischer11] <a name="Fischer11"/>
  Sebastian Fischer, Oleg Kiselyov, Chung-Chieh Shan (2011)
  [Purely functional lazy nondeterministic programming](http://okmij.org/ftp/Haskell/FLP/lazy-nondet.pdf)
