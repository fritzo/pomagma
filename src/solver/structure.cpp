#include <pomagma/solver/structure.hpp>

namespace pomagma {
namespace solver {

const char* term_arity_name(TermArity arity) {
    static const char* names[] = {
        "IVAR", "NVAR", "APP", "JOIN", "TOP", "BOT", "I", "K", "B", "C", "S",
    };
    return names[static_cast<size_t>(arity)];
}

Structure::Structure() {
    POMAGMA_INFO("Initializing solver::Structure");

    // Initialize vectors for 1-based indexing.
    term_arity_.resize(1);
    less_arg_.resize(1);

    // Initialize atoms.
    new_term(TermArity::TOP);
    new_term(TermArity::BOT);
    new_term(TermArity::I);
    new_term(TermArity::K);
    new_term(TermArity::B);
    new_term(TermArity::C);
    new_term(TermArity::S);

    if (POMAGMA_DEBUG_LEVEL) {
        assert_valid();
    }
}

Structure::~Structure() {
    if (POMAGMA_DEBUG_LEVEL) {
        assert_valid();
    }
}

void Structure::assert_valid() {
    POMAGMA_INFO("Validating solver::Structure");

    // Check atoms.
    POMAGMA_ASSERT(term_arity(TermAtom::TOP) == TermArity::TOP, "Missing TOP");
    POMAGMA_ASSERT(term_arity(TermAtom::BOT) == TermArity::BOT, "Missing BOT");
    POMAGMA_ASSERT(term_arity(TermAtom::I) == TermArity::I, "Missing I");
    POMAGMA_ASSERT(term_arity(TermAtom::K) == TermArity::K, "Missing K");
    POMAGMA_ASSERT(term_arity(TermAtom::B) == TermArity::B, "Missing B");
    POMAGMA_ASSERT(term_arity(TermAtom::C) == TermArity::C, "Missing C");
    POMAGMA_ASSERT(term_arity(TermAtom::S) == TermArity::S, "Missing S");
}

}  // namespace solver
}  // namespace pomagma
