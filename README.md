# Pomagma

A deductive database for partially ordered magmas.<br />
An experiment in coding under extensional semantics.<br />
A lens into a supremely beautiful mathematical object.

## Roadmap

### Minimal System

- Messaging
    - Serialize structural db via protobuf
    - Serialize pcfg language via protobuf
    - Implement general persistent serialization via hdf5
- Master
    - Sketch master controller in python
- Mixer
    - Implement API
    - Implement expression sampler
        - Sampler computes ob probabilities in a single background thread
        - Supports operations: insert, unsafe_merge, unsafe_remove
        - Sampler is parametrized by probabilistic grammar
    - Implement copy_from operations for all types and for theory
        - Implement sorting version for compaction & efficiency
    - Make DenseSet::, Carrier::unsafe_insert safe as try_insert()
    - Flesh out unit test to exercise all methods
        - Add tests for DenseSet::Iterator2, 3
    - Add full test that builds 14400-element H4 group via insert requests
- Compiler
    - Get skj.theory.cpp to compile (probably by fixing pomagma/compiler.py)

### Interactive System

- Navigator Server
    - Adapt syntactic algorithms from [Johann](http://github.com/fritzo/Johann)
- Navigator Client
    - Implement HTML5 UI

### Scalable System

- Aggregator
    - Implement following merge logic in mixer
    - Assume only forward-mapping tables
        - Work out injective function merge logic
    - Use 32-bit ob indices
- Trimmer
    - Read globe; randomly prune to given size; write

### Evolvable System

- Theorist
    - Adapt auto conjecturing algorithms from [Johann](http://github.com/fritzo/Johann)
    - Implement via CUDA/GPU or Eigen+OpenMP
- Linguist
    - Adapt language optimization algorithms from [Johann](http://github.com/fritzo/Johann)
    - Implement via CUDA/GPU or Eigen+OpenMP

## System Architecture

![Architecture](pomagma/raw/master/doc/architecture.png)

