Pomagma
=======

Equational reasoning in partially ordered magmas

Roadmap
-------

- Merge inverse_bin_fun into BinaryFunction and SymmetricFunction
    - Abstract out the Vlr_Data and VXx_Data classes, following base_bin_rel
- Reimplement DenseSet using std::atomic<Word> instead of Word
    - In DenseSet::Iterator, store raw word data instead of set reference
    - Implement DenseSet::IntersectionIterator2, 3, 4 for delayed intersection
    - Add .iter(), .iter_insn(-), .iter_insn(-,-) methods to DenseSet
- Work out relaxed-vs-strict operation and monotonicity requirements
    - Carrier is already in good shape
    - Functions should make sure .defined(-) matches .value(-)
    - All EnforceTasks should be monotonic and allow relaxed memory order
    - Maybe provide monotone-only wrapper classes for Functions & Relations
      (monotone wrappers would be used in enforcement and in theory.hpp)
- Get sk.theory.cpp to compile
    - This is mundane no-brain python work, after BinaryFunction's
      InverseIterator and InverseRangeIterator are implemented
- Implement copy_from operations for all types and for theory
    - Implement sorting version for compaction & efficiency
- Implement binary dump operations for an external insert/remove process
    - Maybe implement binary load at same time
- Add dump/insert/remove interface to server
- Add system test that builds 14400-element H4 group via insert requests
