// Reduction engine.
//
// This implements a number of ideas for efficient / optimal beta-eta reduction.
// - Beta-eta reduce using the algorith of Boulifa and Mezghiche (2003).
// - Cons-hash terms to implement Hyland's graph reduction.
// - Memoize to implement call-by-need (optimal combinator reduction).
// - Eagerly linearly reduce to limit memoizing storage to linear normal forms.
//
// Feature development plan:
// - Collect and curate unit test cases.
// - Collect and curate benchmark cases.
// - Implement forward-chaining merging.
// - Memoize all methods.
// - Provide any-time computation instead of budget parameter.
// - Verify reduce() and print() behavior on rational normal forms.
// - Add binary operation JOIN.
//   - Maybe use first 2 bits to dispatch among {atom, var, app, join}.
//   - Or split into {var, app, join, rand} and reserve some vars for atoms.
// - Support untyped nondeterminism.
// - Support a few basic types-as-closures.
// - Support typed nondeterminism.
// - Cleverly reduce total variable count, eg de Bruijn variables.
// - Persistence.
// - Garbage collection.
// - Implement optimized numerals with gmp.
// - Factor this out as independent project/repo with zmq interface.
//
// Question:
// Does reduce() converge with finite budget on all rational combinators?
// What about on all rational lambda terms? Are the two the same?
//
// Refactoring Idea:
// The data structures here are mostly for memoization. They all need to
// support .insert(), .merge(), and .find() (and later maybe .gc()).  Why not
// provide a library of container data structures that all support
// forward-chaining .merge() operations, serving the purpose that the original
// pomagma directory served in Johann?

#pragma once

#include <cstdlib>
#include <pomagma/reducer/obs.hpp>
#include <pomagma/util/util.hpp>
#include <set>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace pomagma {
namespace reducer {

// Public methods of the Engine are restricted to closed obs:
// inputs must be closed and return values will be closed.
class Engine : noncopyable {
   public:
    enum : Ob {
        atom_I = 1,
        atom_K = 2,
        atom_B = 3,
        atom_C = 4,
        atom_S = 5,
        atom_BOT = 6,
        atom_TOP = 7,
        atom_count = 7
    };

    Engine();
    ~Engine();

    bool validate(std::vector<std::string>& errors) const;
    void reset();

    // Every ob is zero, a variable, an atom, or an app.
    // Only atoms and apps are public.
    static bool is_atom(Ob ob) { return 0 < ob and ob <= atom_count; }
    static bool is_app(Ob ob) { return atom_count < ob; }

    // If an ob is an app, then it can be decomposed into lhs and rhs.
    Ob get_lhs(Ob val) const;
    Ob get_rhs(Ob val) const;

    // Application, eagerly linear-beta-eta reducing.
    Ob app(Ob lhs, Ob rhs);

    // Result of reduce() will be normal unless budget runs out.
    Ob reduce(Ob ob, size_t& budget);
    bool is_normal(Ob ob) const;

   private:
    void assert_valid() const;
    void assert_ob(Ob ob) const {
        POMAGMA_ASSERT(is_var(ob) or rep_table_.find(ob) != rep_table_.end(),
                       "Ob not found: " << ob);
    }
    void assert_closed(Ob ob) const {
        assert_ob(ob);
        POMAGMA_ASSERT(is_closed(ob), "ob is not closed: " << print(ob));
    }
    void assert_weak_red(Ob ob) const {
        assert_ob(ob);
        if (Ob ob_red = map_find(rep_table_, ob).red) {
            Ob ob_red_red = map_find(rep_table_, ob_red).red;
            POMAGMA_ASSERT(ob_red_red == 0 or ob_red_red == ob_red,
                           "ob rep chain is not normalized: " << print(ob));
        }
    }

    // Debug printing.
    void append(Ob ob, std::ostream& os) const;
    std::string print(Ob ob) const;
    std::string print(const std::vector<Ob>& obs) const;

    // Variables are only for internal use.
    static bool is_var(Ob ob) { return ob < 0; }
    bool is_closed(Ob ob) const {
        return abstract_table_.find(ob) == abstract_table_.end();
    }
    Ob app(Ob lhs, Ob rhs, size_t& budget, Ob begin_var);
    Ob reduce(Ob term, size_t& budget, Ob begin_var);
    Ob pop(std::vector<Ob>& stack, Ob& end_var);

    // Term constructors.
    Ob create_var(Ob var);
    Ob get_var(Ob var);  // Create if not found.
    Ob create_app(Ob lhs, Ob rhs);
    Ob get_app(Ob lhs, Ob rhs);  // Create if not found.

    // Eta-abstraction.
    // Eqn: abstract(var, body) == map_find(abstract(body), var).
    Ob abstract(Ob var, Ob body);
    const std::unordered_map<Ob, Ob>& abstract(Ob body) const;  // Curried.

    // Forward-chaining inference.
    // TODO How long to rep chains persist? How to deal with references?
    void rep_normalize(Ob& ob) const;
    void merge(Ob dep);

    // Algebraic structure of the APP binary relation.
    // These all contain the same tuples, but with different indexing.
    // These are adapted from:
    // atlas/micro/binary_function.hpp
    // atlas/micro/inverse_bin_fun.hpp
    std::unordered_map<ObPair, Ob, ObPairHash> LRv_table_;
    std::unordered_map<Ob, ObPairSet> Lrv_table_;
    std::unordered_map<Ob, ObPairSet> Rlv_table_;
    std::unordered_map<Ob, ObPairSet> Vlr_table_;

    // Abstraction table : body -> var -> abstraction.
    // This table omits a few cheap-to-compute abstractions:
    // - abstract(x, TOP) = TOP
    // - abstract(x, BOT) = BOT
    // - abstract(x, x) = I
    // - abstract(x, y) = APP K y, if x does not occur in y.
    std::unordered_map<Ob, std::unordered_map<Ob, Ob>> abstract_table_;

    // Directed structure.
    // .lhs and .rhs are used for pattern matching and read-back.
    // .red is either self (for new terms), another term (for non-normal forms)
    // or zero (for normalized terms).
    // TODO Can we really use this for both reduction and merging?
    //   Note that no two normal forms can ever be merged, but it is unclear
    //   how to orient non-normalized mergers.
    //   See operational_semantics.text (2016:01:29-02:28) (H2)
    struct Term {
        Ob lhs;
        Ob rhs;
        Ob red;  // Also used for merging.
    };
    std::unordered_map<Ob, Term> rep_table_;

    // Forward-chaining inference state.
    std::set<Ob> merge_queue_;
};

inline Ob Engine::get_lhs(Ob val) const {
    assert_closed(val);
    POMAGMA_ASSERT1(is_app(val), "tried to get_lhs of non-app: " << print(val));
    Ob lhs = map_find(rep_table_, val).lhs;
    assert_closed(lhs);
    return lhs;
}

inline Ob Engine::get_rhs(Ob val) const {
    assert_closed(val);
    POMAGMA_ASSERT1(is_app(val), "tried to get_rhs of non-app: " << print(val));
    Ob rhs = map_find(rep_table_, val).rhs;
    assert_closed(rhs);
    return rhs;
}

inline Ob Engine::app(Ob lhs, Ob rhs) {
    assert_closed(lhs);
    assert_closed(rhs);
    size_t budget = 0;
    Ob begin_var = -1;
    return app(lhs, rhs, budget, begin_var);
}

inline Ob Engine::reduce(Ob ob, size_t& budget) {
    assert_closed(ob);
    if (not budget) return ob;
    Ob begin_var = -1;
    ob = reduce(ob, budget, begin_var);
    assert_closed(ob);
    return ob;
}

inline bool Engine::is_normal(Ob ob) const {
    assert_closed(ob);
    // TODO Are atoms like DIV and A normal? If so, how do we guarantee
    // confluence in the presence of equations like DIV = (I | DIV) * <TOP>?
    return not map_find(rep_table_, ob).red;
}

}  // namespace reducer
}  // namespace pomagma
