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
    std::unordered_set<const Term *> constraints;
    for (const auto & ptr : corpus.lines) {
        const Term * term = ptr.get();
        insert_term(constraints, term);
    }
    return {corpus, std::move(constraints)};
};

namespace {

inline void propagate_constraint (
    const const Term * constraint,
    const std::unordered_map<const Term *, State> & states,
    std::unordered_map<const Term *, ste::vector<State> & message_queues,
    intervals::Approximator & approximator)
{
    const string & name = constraint->name;
    switch (constraint->arity) {
        case NULLARY_FUNCTION: {
            const Term * val = constraint;
            message_queues[val].push_back(approximator.nullary_function(name));
        } break;

        case INJECTIVE_FUNCTION: {
            if (name == "QUOTE") break; // QUOTE is not monotone
            const Term * key = constraint->args[0];
            const Term * val = constraint;
            message_queues[val].push_back(
                approximator.lazy_injective_function_key(name, key));
            message_queues[key].push_back(
                approximator.lazy_injective_function_val(name, val));
        } break;

        case BINARY_FUNCTION: {
            const Term * lhs = constraint->args[0];
            const Term * rhs = constraint->args[1];
            const Term * val = constraint;
            message_queues[val].push_back(
                approximator.lazy_binary_function_lhs_rhs(name, lhs, rhs));
            message_queues[rhs].push_back(
                approximator.lazy_binary_function_lhs_val(name, lhs, val));
            message_queues[lhs].push_back(
                approximator.lazy_binary_function_rhs_val(name, rhs, val));
        } break;

        case SYMMETRIC_FUNCTION: {
            const Term * lhs = constraint->args[0];
            const Term * rhs = constraint->args[1];
            const Term * val = constraint;
            message_queues[val].push_back(
                approximator.lazy_symmetric_function_lhs_rhs(name, lhs, rhs));
            message_queues[rhs].push_back(
                approximator.lazy_symmetric_function_lhs_val(name, lhs, val));
            message_queues[lhs].push_back(
                approximator.lazy_symmetric_function_lhs_val(name, rhs, val));
        } break;

        case UNARY_RELATION: {
            const Term * key = constraint->args[0];
            const Term * val = constraint;
            // propagate truth value up to val as if it were quoted
            message_queues[val].push_back(
                approximator.unary_relation(name, key));
        } break;

        case BINARY_RELATION: {
            const Term * lhs = constraint->args[0];
            const Term * rhs = constraint->args[1];
            const Term * val = constraint;
            // propagate truth value up to val as if it were quoted
            message_queues[val].push_back(
                approximator.binary_relation(name, lhs, rhs));
            // propagate constraints down to lhs, rhs
            if (name == "LESS") {
                message_queues[lhs].push_back(approximator.less_rhs(rhs));
                message_queues[rhs].push_back(approximator.less_lhs(lhs));
            } else if (name == "NLESS") {
                message_queues[lhs].push_back(approximator.nless_rhs(rhs));
                message_queues[rhs].push_back(approximator.nless_lhs(lhs));
            }
        } break;

        case VARIABLE: break; // no information
        case HOLE: break; // no information
    }
}

// Returns number of variables that have changed.
// This is guaranteed to have time complexity O(#constraints).
inline size_t propagate_step (
    const std::unordered_map<const Term *, State> & states,
    std::unordered_map<const Term *, std::vector<State>> & message_queues,
    const Problem & problem,
    intervals::Approximator & approximator)
{
    for (const Term * constraint : problem.constraints) {
        propagate_constraint(constraint, states, message_queues, approximator);
    }

    size_t change_count = 0;
    for (auto & i : states) {
        const Term * term = i.first;
        State & state = i.second;
        std::vector<State> & messages = message_queues.find(term)->second;
        const State updated_state = approximator.lazy_fuse(messages);
        messages.clear();
        if (updated_state != state) {
            POMAGMA_ASSERT1(approximator.refines(updated_state, state),
                "propagation was not monotone");
        }
        state = updated_state;
        ++change_count;
    }

    POMAGMA_DEBUG("propagation found " << change_count << " changes");
    return change_count;
}

} // namespace

Solution solve (const Problem & problem, intervals::Approximator & approximator)
{
    POMAGMA_DEBUG("Propagating " << problem.constraints.size() << " variables");

    std::unordered_map<const Term *, State> states;
    for (const Term * term : problem.constraints) {
        state.insert({term, approximator.unknown()});
    }

    std::unordered_map<const Term *, std::vector<State>> message_queues;
    while (propagate_step(states, message_queues, problem, approximator)) {}

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
