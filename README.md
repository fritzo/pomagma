Pomagma
=======

Equational reasoning in partially ordered magmas

Roadmap
-------

- Get skj.theory.cpp to compile (probably by fixing pomagma/compiler.py)
- Make DenseSet::, Carrier::unsafe_insert safe as try_insert()
- Flesh out unit test to exercise all methods
    - Add tests for DenseSet::Iterator2, 3
- Implement copy_from operations for all types and for theory
    - Implement sorting version for compaction & efficiency
- Implement binary dump operations for an external insert/remove process
    - Maybe implement binary load at same time
- Add dump/insert/remove interface to server
- Add system test that builds 14400-element H4 group via insert requests
