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

    // Check terms.
    const Term max_term = term_arity_.size() - 1;
    for (Term term = 1; term <= max_term; ++term) {
        const TermArity arity = term_arity(term);
        switch (arity) {
            case TermArity::IVAR: {
                const unsigned rank = ivar_arg(term);
                POMAGMA_ASSERT_EQ(term, ivar(rank));
                break;
            }
            case TermArity::NVAR: {
                const std::string& name = nvar_arg(term);
                POMAGMA_ASSERT_EQ(term, nvar(name));
                break;
            }
            case TermArity::APP: {
                Term lhs;
                Term rhs;
                std::tie(lhs, rhs) = app_arg(term);
                POMAGMA_ASSERT_EQ(term, app(lhs, rhs));
                break;
            }
            case TermArity::JOIN: {
                Term lhs;
                Term rhs;
                std::tie(lhs, rhs) = join_arg(term);
                POMAGMA_ASSERT_EQ(term, join(lhs, rhs));
                break;
            }
            default:
                break;
        }
    }

    // Check literals.
    const Literal max_lit = less_arg_.size() - 1;
    for (Literal lit = 1; lit <= max_lit; ++lit) {
        Term lhs;
        Term rhs;

        std::tie(lhs, rhs) = literal_arg(lit);
        POMAGMA_ASSERT_EQ(lit, less(lhs, rhs));

        std::tie(lhs, rhs) = literal_arg(-lit);
        POMAGMA_ASSERT_EQ(-lit, nless(lhs, rhs));
    }
}

Term Structure::choose_random_term(rng_t& rng) const {
    const Term max_term = term_arity_.size() - 1;
    return std::uniform_int_distribution<Term>(1, max_term)(rng);
}

Literal Structure::choose_random_literal(rng_t& rng) const {
    const Literal max_lit = less_arg_.size() - 1;
    Literal lit = std::uniform_int_distribution<Literal>(1, max_lit)(rng);
    return std::bernoulli_distribution(0.5)(rng) ? lit : -lit;
}

}  // namespace solver
}  // namespace pomagma
