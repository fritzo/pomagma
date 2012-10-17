Pomagma
=======

A deductive database for partially ordered magmas.<br />
An experiment in coding under extensional semantics.<br />
A lens into a supremely beautiful mathematical object.

Roadmap
-------

- Structure
    - Implement persistent serializer
    - Create core structures from theory
- Language
    - Add python language server or python+cpp file reading libraries
    - Add langauges to git: sk, skj
- Theory
    - Implement core writer (for Hindley's extensionality axioms)
- Grower
    - Figure out how to set item_dim at runtime
    - Implement expression sampler
    - Implement dump, load operations
    - Implement language reading & data structure
    - Make Carrier::unsafe_insert safe as try_insert()
    - Flesh out unit test to exercise all methods
        - Add tests for DenseSet::Iterator2, 3
    - Add full test that builds 14400-element H4 group via insert requests
- Compiler
    - Get skj.theory.cpp to compile (probably by fixing pomagma/compiler.py)
- Navigator Server
    - Adapt syntactic algorithms from [Johann](http://github.com/fritzo/Johann)
- Navigator Client
    - Implement HTML5 UI
    - Implement native mobile UIs
- Aggregator
    - Implement following merge logic in grower
    - Assume only forward-mapping tables
        - Work out injective function merge logic
    - Use 32-bit ob indices
- Trimmer
    - Read globe; randomly prune to given size; write
- Theorist
    - Adapt auto conjecturing algorithms from [Johann](http://github.com/fritzo/Johann)
    - Implement via CUDA/GPU or Eigen+OpenMP
- Linguist
    - Adapt language optimization algorithms from [Johann](http://github.com/fritzo/Johann)
    - Implement via CUDA/GPU or Eigen+OpenMP
- Controller
    - Implement master controller in python
    - Use boto to provision machines

Milestones
----------

- Minimum: run grower system tests
- Interactive: implement navigator as web-app
- Scalable: implement aggregator, trimmer
- Evolvable: implement linguist, theorist

System Architecture
-------------------

![Architecture](pomagma/raw/master/doc/architecture.png)

