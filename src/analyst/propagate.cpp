#include <pomagma/analyst/propagate.hpp>
#include <unordered_map>

namespace pomagma {
namespace propagate {

//----------------------------------------------------------------------------
// parsing

Theory parse_theory (
    const std::vector<std::string> & polish_facts __attribute__((unused)),
    std::vector<std::string> & error_log __attribute__((unused)))
{
    // TODO define a parser as in src/analyst/simplify.cpp Simplify::Reducer
    return Theory();
}

//----------------------------------------------------------------------------
// propagation

using ::pomagma::intervals::BELOW;
using ::pomagma::intervals::ABOVE;
using ::pomagma::intervals::NBELOW;
using ::pomagma::intervals::NABOVE;

typedef intervals::Approximation State;

namespace {

inline void propagate_constraint (
    const Term * term,
    const std::unordered_map<const Term *, State> & states,
    std::unordered_map<const Term *, std::vector<State>> & message_queues,
    Approximator & approximator)
{
    const std::string & name = term->name;
    switch (term->arity) {
        case NULLARY_FUNCTION: {
            const Term * val = term;
            message_queues[val].push_back(approximator.nullary_function(name));
        } break;

        case INJECTIVE_FUNCTION: {
            if (name == "QUOTE") break; // QUOTE is not monotone
            TODO("propagate injective_function " << name);
        } break;

        case BINARY_FUNCTION:
        case SYMMETRIC_FUNCTION: {
            const Term * lhs = term->args[0].get();
            const Term * rhs = term->args[1].get();
            const Term * val = term;
            message_queues[val].push_back(
                approximator.lazy_binary_function_lhs_rhs(
                    name, map_find(states, lhs), map_find(states, rhs)));
            message_queues[rhs].push_back(
                approximator.lazy_binary_function_lhs_val(
                    name, map_find(states, lhs), map_find(states, val)));
            message_queues[lhs].push_back(
                approximator.lazy_binary_function_rhs_val(
                    name, map_find(states, rhs), map_find(states, val)));
        } break;

        case UNARY_RELATION: {
            TODO("propagate unary_relation " << name);
        } break;

        case BINARY_RELATION: {
            const Term * lhs = term->args[0].get();
            const Term * rhs = term->args[1].get();
            if (name == "LESS") {
                message_queues[lhs].push_back(
                    approximator.less_rhs(map_find(states, rhs)));
                message_queues[rhs].push_back(
                    approximator.less_lhs(map_find(states, lhs)));
            } else if (name == "NLESS") {
                message_queues[lhs].push_back(
                    approximator.nless_rhs(map_find(states, rhs)));
                message_queues[rhs].push_back(
                    approximator.nless_lhs(map_find(states, lhs)));
            } else {
                TODO("propagate binary_relation " << name);
            }
        } break;

        case EQUAL: {
            const Term * lhs = term->args[0].get();
            const Term * rhs = term->args[1].get();
            message_queues[lhs].push_back(map_find(states, rhs));
            message_queues[rhs].push_back(map_find(states, lhs));
        } break;

        case HOLE: break; // no information
        case VAR: break; // no information
    }
}

// this should have time complexity O(#constraints)
inline size_t propagate_step (
    std::unordered_map<const Term *, State> & states,
    std::unordered_map<const Term *, std::vector<State>> & message_queues,
    const Theory & theory,
    Approximator & approximator)
{
    for (const Term * term : theory.terms) {
        propagate_constraint(term, states, message_queues, approximator);
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
            state = updated_state;
            ++change_count;
        }
        if (approximator.lazy_is_valid(state) == Trool::FALSE) {
            POMAGMA_DEBUG("solution is invalid");
            return 0;
        }
    }

    POMAGMA_DEBUG("propagation found " << change_count << " changes");
    return change_count;
}

} // namespace

Trool lazy_validate (const Theory & theory, Approximator & approximator)
{
    POMAGMA_DEBUG("Propagating " << theory.terms.size() << " variables");

    std::unordered_map<const Term *, State> states;
    for (const Term * term : theory.terms) {
        states.insert({term, approximator.unknown()});
    }

    std::unordered_map<const Term *, std::vector<State>> message_queues;
    while (propagate_step(states, message_queues, theory, approximator)) {}

    Trool is_valid = Trool::TRUE;
    for (const auto & i : states) {
        is_valid = and_trool(is_valid, approximator.lazy_is_valid(i.second));
    }
    return is_valid;
}

} // namespace propagate
} // namespace pomagma
