#pragma once

#include <algorithm>
#include <pomagma/solver/syntax.hpp>
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

    bool is_true(Literal lit) const {
        return std::binary_search(true_literals_.begin(), true_literals_.end(),
                                  lit);
    }

    // TODO Add checkpointing interface: push, pop.

   private:
    LiteralSet true_literals_;
};

}  // namespace solver
}  // namespace pomagma
