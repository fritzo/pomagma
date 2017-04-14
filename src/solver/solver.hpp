#pragma once

#include <pomagma/solver/structure.hpp>
#include <pomagma/util/util.hpp>

namespace pomagma {
namespace solver {

// Theory solver for the theory H*.
class HstarSolver : noncopyable {
   public:
    // Make assumptions; if the assumptions are consistent, then return an
    // updated HstarSolver and record conclusions, otherwise return nullptr.
    // Initial value of conclusions is ignored.
    HstarSolver* try_assume(const LiteralSet& assumptions,
                            LiteralSet& conclusions);

   private:
    LiteralSet true_literals_;
};

// Satisfiability Modulo Theory solver for the Hstar theory.
class SmtSolver {
    SmtSolver();
};

}  // namespace solver
}  // namespace pomagma
