Pomagma
=======

A deductive database for partially ordered magmas.<br />
An experiment in coding under extensional semantics.<br />
A lens into a supremely beautiful mathematical object.<br />
A toy model of Lakatosian mathematical evolution.<br />
A mashup of first-person-shooter with theorem prover.<br />
A distributed rewrite of [Johann](Johann) with an artsy front-end.

Roadmap
-------

- Language
    - Add languages to git: skjo
- Theory
    - Implement extensionality for quote/eval rules (skjo)
- Atlas
- Corpus
    - Decide on representation
    - Decide on ownership/personalization rules
- Compiler
- Grower
    - Flesh out unit test to exercise all methods
        - Add tests for DenseSet::Iterator2, 3
    - Profile & optimize using system tests for sk, skj
- Aggregator
- Trimmer
    - Read globe; randomly prune to given size; write
- Navigator Server
    - Adapt syntactic algorithms from [Johann](http://github.com/fritzo/Johann)
- Navigator Client
    - Implement HTML5 UI
- Theorist
    - Adapt auto conjecturing algorithms from [Johann](Johann)
    - Implement via CUDA/GPU or Eigen+OpenMP
- Linguist
    - Adapt language optimization algorithms from [Johann](http://github.com/fritzo/Johann)
    - Implement via CUDA/GPU or Eigen+OpenMP
- Controller
    - Implement master controller via python
    - Use boto to provision machines

Milestones
----------

- Minimum: run grower system tests (h4, sk, skj) DONE
- Scalable: implement aggregator, trimmer
- Interactive: implement navigator as web-app
- Evolvable: implement linguist, theorist

System Architecture
-------------------

![Architecture](doc/architecture.png)

- Language - a probabilistic grammar defining an algebra's generators
- Theory - inference rules and facts defining an algebra's relations
- Atlas - a finite substructure of the algebra; a knowledge base
- Corpus - a working set of interesting terms/positions in the algebra
- Compiler - an optimizing compiler for forward-chaining inference
- Grower - a parallel Todd-Coxeter rules engine
- Aggregator - joins charts from growers into a global atlas
- Trimmer - cuts off pieces of the structure for further growth
- Navigator - a user interface for exploring the mapped algebra
- Theorist - statistically conjectures new relations
- Linguist - a Bayesian grammar optimizer / MCMC sampler

