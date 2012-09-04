Pomagma
=======

Equational reasoning in partially ordered magmas.

Roadmap
-------

- Merge inverse_bin_fun into BinaryFunction and SymmetricFunction.
    - Abstract out the Vlr_Data and VXx_Data classes, following base_bin_rel.
- Work out relaxed-vs-strict operation and monotonicity requirements.
    - Carrier is already in good shape.
    - All EnforceTasks should be monotonic and allow relaxed memory order.
    - Maybe provide monotone-only wrapper classes for Functions & Relations.
      Monotone wrappers are used in enforcement and in theory.hpp.
- Add Carrier::DepIterator(Ob rep) to iterate over equivalence classes.
    - This can speed up VariousFunction::merge(dep,rep) methods.
- Get sk.theory.cpp to compile.
    - This is mundane no-brain python work, after BinaryFunction's
      InverseIterator and InverseRangeIterator are implemented.
- Implement binary dump operations for an external insert/remove process.
    - Maybe implement binary load at same time.
- Add dump/insert/remove interface to server.
- Add system test that builds 14400-element H4 group via insert requests.
