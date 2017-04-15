#pragma once

#include <memory>
#include <pomagma/solver/syntax.hpp>
#include <pomagma/solver/theory_solver.hpp>
#include <pomagma/util/util.hpp>

namespace pomagma {
namespace solver {

// Satisfiability Modulo Theory solver for the Hstar theory.
class SmtSolver {
    SmtSolver();

    bool try_assume(const LiteralSet& assumptions, LiteralSet& conclusions);

    // TODO Add checkpointing interface: push, pop.

   private:
    std::vector<std::unique_ptr<HstarSolver>> theory_solver_stack_;
};

}  // namespace solver
}  // namespace pomagma
