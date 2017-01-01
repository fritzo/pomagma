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

## References

- [Scott76] <a name="Scott76"/>
  Dana Scott (1976)
  [Datatypes as Lattices](http://www.cs.ox.ac.uk/files/3287/PRG05.pdf)
- [Obermeyer09] <a name="Obermeyer09"/>
  Fritz Obermeyer (2009)
  [Automated Equational Reasoning in Nondeterministic &lambda;-Calculi Modulo Theories H*](http://fritzo.org/thesis.pdf)
- [Feferman05] <a name="Feferman05"/>
  Solomon Feferman (2005)
  [Predicativity](http://math.stanford.edu/~feferman/papers/predicativity.pdf)
- [Fischer11] <a name="Fischer11"/>
  Sebastian Fischer, Oleg Kiselyov, Chung-Chieh Shan (2011)
  [Purely functional lazy nondeterministic programming](http://okmij.org/ftp/Haskell/FLP/lazy-nondet.pdf)
