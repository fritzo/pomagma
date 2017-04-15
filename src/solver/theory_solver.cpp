#include <pomagma/solver/theory_solver.hpp>

namespace pomagma {
namespace solver {

HstarSolver* HstarSolver::try_assume(const LiteralSet& assumptions,
                                     LiteralSet& conclusions) {
    POMAGMA_ASSERT(!assumptions.empty(), "Nothing to assume");
    conclusions.clear();

    TODO("Use Huet's algorithm?");
}

}  // namespace solver
}  // namespace pomagma
