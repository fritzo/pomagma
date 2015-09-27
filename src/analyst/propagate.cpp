#include <pomagma/analyst/propagate.hpp>

namespace pomagma {
namespace propagate {

static void insert_term (
    std::unordered_set<const Term *> set,
    const Term * term)
{
    if (set.insert(term).second) {
        if (Term * arg = term.args[0].get()) { insert_term(set, arg); }
        if (Term * arg = term.args[1].get()) { insert_term(set, arg); }
    }
}

Problem formulate (std::unique_ptr<Corpus> corpus)
{
    std::unordered_set<const Term *> terms;
    for (const auto & ptr : corpus.lines) {
        const Term * term = ptr.get();
        insert_term(terms, term);
    }

    std::unordered_map<const Term *, std::vector<Constraint>> constraints;
    for (const Term * term : terms) {
        switch (term.arity) {
            case NULLARY_FUNCTION:
                constraints[term].push_back({term, VOID});
                break;

            case INJECTIVE_FUNCTION:
                constraints[term].push_back({term, KEY});
                constraints[term.args[0].get()].push_back({term, VAL});
                break;

            case BINARY_FUNCTION:
                constraints[term].push_back({term, LHS_RHS});
                constraints[term.args[0].get()].push_back({term, RHS_VAL});
                constraints[term.args[1].get()].push_back({term, LHS_VAL});
                break;

            case SYMMETRIC_FUNCTION:
                constraints[term].push_back({term, LHS_RHS});
                constraints[term.args[0].get()].push_back({term, RHS_VAL});
                if (term.args[0].get() != term.args[1].get()) {
                    constraints[term.args[1].get()].push_back({term, LHS_VAL});
                }
                break;

            default:
                TODO("handle relations");
        }
    }

    return {corpus, std::move(constraints)};
};

inline State propagate_constraint (
    const Constraint & constraint,
    const std::unordered_map<State> & prev_states,
    intervals::Approximator & approximator)
{
    State state;
    TODO("deal with obs for known states");
    const Term & term = * constraint.term;
    switch (term.arity) {
        case NULLARY_FUNCTION: {
            POMAGMA_ASSERT_EQ(constraint.direction, VOID);
            for (Parity p : {BELOW, ABOVE, NBELOW, NABOVE}) {
                state[p] = approximator.lazy_nullary_function(term.name, p);
            }
        } break;

        case INJECTIVE_FUNCTION: {
            switch (constraint.direction) {
                case KEY: {
                    for (Parity p : {BELOW, ABOVE, NBELOW, NABOVE}) {
                        state[p] = TODO
                } break;

                case VAL: {
                } break;

                default:
                    POMAGMA_ERROR("bad direction: " << constraint.direction);
            }
            POMAGMA_ASSERT_EQ(constraint.direction, VOID);
            for (Parity p : {BELOW, ABOVE, NBELOW, NABOVE}) {
                state[p] = approximator.lazy_nullary_function(term.name, p);
            }
        } break;

        default: TODO("switch(arity): for each parity: propagate ");
    }
    return state;
}

inline State fuse_states(
    const std::vector<State> & states,
    intervals::Approximator & approximator)
{
    State result;
    auto i = states.begin();
    if (i == states.end()) {
        return approximator.unknown();
    }
    result = states[0];
    while (++i != states.end()) {
        const auto & state = *i;
        for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
            result[p] = (result[p] && state[p])
                      ? approximator.try_union(result[p], state[p])
                      : 0;
        }
    }
    return result;
}

inline State propagate_variable (
    const std::vector<Constraint> & constraints,
    const std::unordered_map<State> & states,
    intervals::Approximator & approximator)
{
    std::vector<State> components;
    components.reserve(constraints.size());
    for (const auto & constraint : constraints) {
        components.push_back(
            propagate_constraint(constraint, states, approximator));
    }
    return fuse_states(components);
}

// Returns number of variables that have changed.
// This is guaranteed to have time complexity O(#constraints).
inline size_t propagate_step (
    std::unordered_map<const Term *, State> & curr_states,
    const std::unordered_map<const Term *, State> & prev_states,
    const Problem & problem,
    intervals::Approximator & approximator)
{
    size_t change_count = 0;
    for (auto & i : curr_states) {
        const Term * term = i.first;
        State & curr_state = i.second;
        const State & prev_state = prev_states.find(term)->second;
        const auto & constraints = problem.constraints.find(term)->second;

        curr_state = propagate_variable(constraints, prev_states, approximator);
        if (curr_state != prev_state) {
            ++change_count;
            POMAGMA_ASSERT1(approximator.refines(curr_state, prev_state);
        }
    }
    POMAGMA_DEBUG("propagation found " << change_count << " changes");
    return change_count;
}

Solution solve (const Problem & problem, intervals::Approximator & approximator)
{
    const size_t size = problem.constraints.size();
    POMAGMA_DEBUG("Propagating problem with " << size << " variables");
    std::unordered_map<const Term *, State> curr_states();
    std::unordered_map<const Term *, State>
        prev_states(size, approximator.unknown());

    while (propagate_step(curr_states, prev_states, problem, approximator)) {
        std::swap(curr_states, prev_states);
    }

    return {std::move(curr_states)};
}

bool is_pending (const Solution & solution)
{
    for (const auto & i : solution.states) {
        for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
            if (not i.second[p]) {
                return true;
            }
        }
    }
    return false;
}

} // namespace propagate
} // namespace pomagma
