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
    static bool is_var(Ob ob) { return ob < 0; }
    static bool is_atom(Ob ob) { return 0 < ob and ob <= atom_count; }
    static bool is_app(Ob ob) { return atom_count < ob; }
    // If an ob is an app, then it can be decomposed into lhs and rhs.
    Ob get_lhs(Ob ob) const;
    Ob get_rhs(Ob ob) const;

    // Application, eagerly linear-beta-eta reducing.
    // TODO FIXME fix begin_var and end_var, following notes/code/vms/eta.py.
    Ob app(Ob lhs, Ob rhs, size_t& budget, Ob begin_var = -1);
    Ob app(Ob lhs, Ob rhs) {
        size_t budget = 0;
        return app(lhs, rhs, budget);
    }

    // TODO Allow nondeterminstic SKJ execution as in combinator.py.
    Ob reduce(Ob term, size_t& budget, Ob begin_var = -1);
    bool is_normal(Ob ob) const { return map_find(rep_table_, ob).red == ob; }

    // TODO
    // void compact();
    // void dump(const string& filename) const;
    // void load(const string& filename);
    // void aggregate_from(const Engine& other);

   private:
    void assert_valid() const;
    void assert_pos(Ob ob) const {
        POMAGMA_ASSERT_LT(0, ob);
        POMAGMA_ASSERT_LT(ob, static_cast<Ob>(rep_table_.size()));
    }
    void assert_red(Ob ob) const {
        assert_pos(ob);
        POMAGMA_ASSERT_EQ(map_find(rep_table_, ob).red, ob);
    }
    void assert_weak_red(Ob ob) const {
        assert_pos(ob);
        Ob red_pos = map_find(rep_table_, ob).red;
        POMAGMA_ASSERT(red_pos == 0 or red_pos == ob,
                       "ob is defined but not normal");
    }

    // Term constructors.
    Ob create_app(Ob lhs, Ob rhs);
    Ob get_app(Ob lhs, Ob rhs);  // Create if not found.

    // Eta-abstraction.
    // Eqn: abstract(var, body) == map_find(abstract(body), var).
    Ob abstract(Ob var, Ob body);
    const std::unordered_map<Ob, Ob>& abstract(Ob body) const;  // Curried.

    // Forward-chaining inference.
    void rep_normalize(Ob& ob) const;
    void merge(Ob dep);

    // Algebraic structure of the APP binary relation.
    // These are adapted from:
    // atlas/micro/binary_function.hpp
    // atlas/micro/inverse_bin_fun.hpp
    std::unordered_map<ObPair, Ob, ObPairHash> LRv_table_;
    std::unordered_map<Ob, ObPairSet> Lrv_table_;
    std::unordered_map<Ob, ObPairSet> Rlv_table_;
    std::unordered_map<Ob, ObPairSet> Vlr_table_;

    // Abstraction table : body -> var -> abstraction.
    std::unordered_map<Ob, std::unordered_map<Ob, Ob>> abstract_table_;
    const std::unordered_map<Ob, Ob> closed_table_;  // Just a default value.

    // Directed structure.
    // lhs and rhs are used for pattern matching and read-back.
    struct Term {
        Ob lhs;
        Ob rhs;
        Ob red;
    };
    std::unordered_map<Ob, Term> rep_table_;

    // Forward-chaining inference state.
    std::set<Ob> merge_queue_;
};

inline Ob Engine::get_lhs(Ob ob) const {
    assert_pos(ob);
    POMAGMA_ASSERT1(is_app(ob), "tried to read lhs of non-app");
    return map_find(rep_table_, ob).lhs;
}

inline Ob Engine::get_rhs(Ob ob) const {
    assert_pos(ob);
    POMAGMA_ASSERT1(is_app(ob), "tried to read rhs of non-app");
    return map_find(rep_table_, ob).rhs;
}

}  // namespace reducer
}  // namespace pomagma
