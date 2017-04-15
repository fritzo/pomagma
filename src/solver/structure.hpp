// Syntax of terms and literals.
//
// Design decisions:
// - Terms are combinators or variables.
// - Literals are either LESS or NLESS.
// - Terms and Literals are represented by various 32-bit integer types.
// - Terms and Literals are cons-hashed by a Structure instance.
// - Memory is never freed.

#pragma once

#include <pomagma/util/util.hpp>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

namespace pomagma {
namespace solver {

// Terms.
typedef uint32_t Term;  // Nonzero.
enum class TermArity { IVAR, NVAR, APP, JOIN, TOP, BOT, I, K, B, C, S };
const char* term_arity_name(TermArity arity);

// enum class TermAtom : Term { TOP = 1, BOT, I, K, B, C, S };
namespace TermAtom {

static constexpr Term TOP = 1;
static constexpr Term BOT = 2;
static constexpr Term I = 3;
static constexpr Term K = 4;
static constexpr Term B = 5;
static constexpr Term C = 6;
static constexpr Term S = 7;

}  // namespace TermAtom

// Literals.
typedef int32_t Literal;  // Nonzero; for each literal x, -x is its negation.
enum class LiteralArity { LESS, NLESS };
const char* literal_arity_name(LiteralArity arity);
inline Literal literal_abs(Literal lit) { return (lit >= 0) ? lit : -lit; }
inline LiteralArity literal_arity(Literal lit) {
    return (lit >= 0) ? LiteralArity::LESS : LiteralArity::NLESS;
}

// Sets of literals are represented as sorted unique vectors.
// TODO Consider wrapping this in a class.
typedef std::vector<Literal> LiteralSet;

// Helper hash function for std::unordered_map<std::pair<Term, Term>, ...>.
struct TermPairHash {
    size_t operator()(const std::pair<Term, Term>& pair) const {
        static_assert(sizeof(Term) == 4, "invalid sizeof(Term)");
        static_assert(sizeof(size_t) == 8, "invalid sizeof(size_t)");
        size_t x = pair.first;
        size_t y = pair.second;
        return (x << 32) | y;
    }
};

// Structures.
class Structure {
   public:
    Structure();
    ~Structure();
    void assert_valid();

    // Term intro forms. Use TermAtom::_ for atoms.
    Term ivar(unsigned rank);
    Term nvar(const std::string& name);
    Term app(Term lhs, Term rhs);
    Term join(Term lhs, Term rhs);

    // Term elim forms.
    TermArity term_arity(Term term) const;
    unsigned ivar_arg(Term term) const;
    const std::string& nvar_arg(Term term) const;
    const std::pair<Term, Term>& app_arg(Term term) const;
    const std::pair<Term, Term>& join_arg(Term term) const;

    // Literal intro forms.
    Literal less(Term lhs, Term rhs);
    Literal nless(Term lhs, Term rhs) { return -less(lhs, rhs); }

    // Literal elim forms.
    const std::pair<Term, Term>& literal_arg(Literal lit) const;

    // Random generation for testing.
    Term choose_random_term(rng_t& rng) const;
    Literal choose_random_literal(rng_t& rng) const;

   private:
    // This internal helper does not preserve validity.
    Term new_term(TermArity arity);

    // Term intro tables.
    std::vector<Term> ivar_;
    std::unordered_map<std::string, Term> nvar_;
    std::unordered_map<std::pair<Term, Term>, Term, TermPairHash> app_;
    std::unordered_map<std::pair<Term, Term>, Term, TermPairHash> join_;

    // Term elim tables.
    std::vector<TermArity> term_arity_;
    std::unordered_map<Term, unsigned> ivar_arg_;
    std::unordered_map<Term, std::string> nvar_arg_;
    std::unordered_map<Term, std::pair<Term, Term>> app_arg_;
    std::unordered_map<Term, std::pair<Term, Term>> join_arg_;

    // Literal tables.
    std::unordered_map<std::pair<Term, Term>, Literal, TermPairHash> less_;
    std::vector<std::pair<Term, Term>> less_arg_;
};

// ---------------------------------------------------------------------------
// Implementations.

inline Term Structure::new_term(TermArity arity) {
    const Term result = term_arity_.size();
    term_arity_.push_back(arity);
    return result;
}

inline Term Structure::ivar(unsigned rank) {
    while (unlikely(rank >= ivar_.size())) {
        const Term term = new_term(TermArity::IVAR);
        const unsigned rank = ivar_.size();
        ivar_.push_back(term);
        ivar_arg_.insert({term, rank});
    }
    if (POMAGMA_DEBUG_LEVEL >= 1) {
        assert_valid();
    }
    return ivar_[rank];
}

inline Term Structure::nvar(const std::string& name) {
    Term& result = nvar_[name];
    if (unlikely(result == 0)) {
        result = new_term(TermArity::NVAR);
        nvar_arg_.insert({result, name});
    }
    if (POMAGMA_DEBUG_LEVEL >= 1) {
        assert_valid();
    }
    return result;
}

inline Term Structure::app(Term lhs, Term rhs) {
    const std::pair<Term, Term> arg(lhs, rhs);
    Term& result = app_[arg];
    if (unlikely(result == 0)) {
        result = new_term(TermArity::APP);
        app_arg_.insert({result, arg});
    }
    if (POMAGMA_DEBUG_LEVEL >= 1) {
        assert_valid();
    }
    return result;
}

inline Term Structure::join(Term lhs, Term rhs) {
    if (lhs == rhs) return lhs;          // Idempotence.
    if (lhs > rhs) std::swap(lhs, rhs);  // Commutativity.
    const std::pair<Term, Term> args(lhs, rhs);
    Term& result = join_[args];
    if (unlikely(result == 0)) {
        result = new_term(TermArity::JOIN);
        join_arg_.insert({result, args});
    }
    if (POMAGMA_DEBUG_LEVEL >= 1) {
        assert_valid();
    }
    return result;
}

inline TermArity Structure::term_arity(Term term) const {
    if (POMAGMA_DEBUG_LEVEL) {
        POMAGMA_ASSERT_LT(term, term_arity_.size());
    }
    return term_arity_[term];
}

inline unsigned Structure::ivar_arg(Term term) const {
    if (POMAGMA_DEBUG_LEVEL) {
        POMAGMA_ASSERT_LT(term, term_arity_.size());
        POMAGMA_ASSERT(term_arity(term) == TermArity::IVAR,
                       "Wrong arity: " << term_arity_name(term_arity(term)));
    }
    auto i = ivar_arg_.find(term);
    POMAGMA_ASSERT1(i != ivar_arg_.end(), "Term not found: " << term);
    return i->second;
}

inline const std::string& Structure::nvar_arg(Term term) const {
    if (POMAGMA_DEBUG_LEVEL) {
        POMAGMA_ASSERT_LT(term, term_arity_.size());
        POMAGMA_ASSERT(term_arity(term) == TermArity::NVAR,
                       "Wrong arity: " << term_arity_name(term_arity(term)));
    }
    auto i = nvar_arg_.find(term);
    POMAGMA_ASSERT1(i != nvar_arg_.end(), "Term not found: " << term);
    return i->second;
}

inline const std::pair<Term, Term>& Structure::app_arg(Term term) const {
    if (POMAGMA_DEBUG_LEVEL) {
        POMAGMA_ASSERT_LT(term, term_arity_.size());
        POMAGMA_ASSERT(term_arity(term) == TermArity::APP,
                       "Wrong arity: " << term_arity_name(term_arity(term)));
    }
    auto i = app_arg_.find(term);
    POMAGMA_ASSERT1(i != app_arg_.end(), "Term not found: " << term);
    return i->second;
}

inline const std::pair<Term, Term>& Structure::join_arg(Term term) const {
    if (POMAGMA_DEBUG_LEVEL) {
        POMAGMA_ASSERT_LT(term, term_arity_.size());
        POMAGMA_ASSERT(term_arity(term) == TermArity::JOIN,
                       "Wrong arity: " << term_arity_name(term_arity(term)));
    }
    auto i = join_arg_.find(term);
    POMAGMA_ASSERT1(i != join_arg_.end(), "Term not found: " << term);
    return i->second;
}

inline Literal Structure::less(Term lhs, Term rhs) {
    const std::pair<Term, Term> arg(lhs, rhs);
    Literal& result = less_[arg];
    if (unlikely(result == 0)) {
        result = less_arg_.size();
        less_arg_.push_back(arg);
    }
    if (POMAGMA_DEBUG_LEVEL >= 1) {
        assert_valid();
    }
    return result;
}

inline const std::pair<Term, Term>& Structure::literal_arg(Literal lit) const {
    if (POMAGMA_DEBUG_LEVEL) {
        POMAGMA_ASSERT(lit, "Literal is null");
        POMAGMA_ASSERT_LT(static_cast<size_t>(literal_abs(lit)),
                          less_arg_.size());
    }
    return less_arg_[literal_abs(lit)];
}

}  // namespace solver
}  // namespace pomagma
