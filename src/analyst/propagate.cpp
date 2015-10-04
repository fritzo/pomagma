#include <pomagma/analyst/propagate.hpp>
#include <pomagma/atlas/macro/structure_impl.hpp>
#include <pomagma/atlas/parser.hpp>
#include <unordered_map>
#include <unordered_set>
#include <tuple>

// defined in pomagma/vendor/farmhash/farmhash.h
namespace util { size_t Hash (const char* s, size_t len); }

namespace pomagma {
namespace propagate {

//----------------------------------------------------------------------------
// parsing

inline size_t hash_data (const void * data, size_t size)
{
    return util::Hash(reinterpret_cast<const char *>(data), size);
}

struct HashExprPtr
{
    size_t operator() (const std::shared_ptr<Expr> & expr) const
    {
        POMAGMA_ASSERT1(expr.get(), "expr is null");
        std::tuple<Arity, size_t, const Expr *, const Expr *> data
        {
            expr->arity,
            hash_data(expr->name.data(), expr->name.size()),
            expr->args[0].get(),
            expr->args[1].get()
        };
        return hash_data(& data, sizeof(data));
    }
};

struct EqExprPtr
{
    bool operator() (
        const std::shared_ptr<Expr> & lhs,
        const std::shared_ptr<Expr> & rhs) const
    {
        POMAGMA_ASSERT1(lhs.get(), "lhs is null");
        POMAGMA_ASSERT1(rhs.get(), "rhs is null");
        return lhs->arity == rhs->arity
           and lhs->name == rhs->name
           and lhs->args[0].get() == rhs->args[0].get()
           and lhs->args[1].get() == rhs->args[1].get();
    }
};

typedef std::unordered_set<std::shared_ptr<Expr>, HashExprPtr, EqExprPtr>
    ExprSet;

class Reducer
{
public:

    Reducer (ExprSet & deduped) : m_deduped(deduped) {}

    typedef std::shared_ptr<Expr> Term;

    Term reduce (
            const std::string & token,
            const NullaryFunction *)
    {
        return new_term(token, NULLARY_FUNCTION);
    }

    Term reduce (
            const std::string & token,
            const InjectiveFunction *,
            const Term & key)
    {
        return new_term(token, INJECTIVE_FUNCTION, key);
    }

    Term reduce (
            const std::string & token,
            const BinaryFunction *,
            const Term & lhs,
            const Term & rhs)
    {
        return new_term(token, BINARY_FUNCTION, lhs, rhs);
    }

    Term reduce (
            const std::string & token,
            const SymmetricFunction *,
            const Term & lhs,
            const Term & rhs)
    {
        return new_term(token, SYMMETRIC_FUNCTION, lhs, rhs);
    }

    Term reduce (
            const std::string & token,
            const UnaryRelation *,
            const Term & key)
    {
        return new_term(token, UNARY_RELATION, key);
    }

    Term reduce (
            const std::string & token,
            const BinaryRelation *,
            const Term & lhs,
            const Term & rhs)
    {
        return new_term(token, BINARY_RELATION, lhs, rhs);
    }

    Term reduce_equal (
            const Term & lhs,
            const Term & rhs)
    {
        return new_term("", EQUAL, lhs, rhs);
    }

    Term reduce_hole ()
    {
        return new_term("", HOLE);
    }

    Term reduce_var (const std::string & name)
    {
        return new_term(name, VAR);
    }

    Term reduce_error (const std::string &)
    {
        return Term();
    }

private:

    Term new_term (
            const std::string & name,
            Arity arity,
            Term arg0 = Term(),
            Term arg1 = Term())
    {
        // kludge to deal with old gcc syntax
        Expr expr = {arity, name, {arg0, arg1}};
        Term result(new Expr(std::move(expr)));
        return * m_deduped.insert(result).first;
    }

    ExprSet & m_deduped;
};

class Parser : public ExprParser<Reducer>
{
public:

    Parser (Signature & signature,
            ExprSet & deduped,
            std::vector<std::string> & error_log) :
        ExprParser<Reducer>(signature, m_reducer, error_log),
        m_reducer(deduped)
    {
    }

private:

    Reducer m_reducer;
};

inline bool is_fact (const Expr & expr)
{
    switch (expr.arity) {
        case UNARY_RELATION:
        case BINARY_RELATION:
        case EQUAL:
            return true;

        default:
            return false;
    }
}

Theory parse_theory (
    Signature & signature,
    const std::vector<std::string> & polish_facts,
    std::vector<std::string> & error_log)
{
    std::vector<std::shared_ptr<Expr>> facts;
    ExprSet deduped;
    {
        Parser parser(signature, deduped, error_log);
        bool error;
        for (size_t i = 0; i < polish_facts.size(); ++i) {
            auto fact = parser.parse(polish_facts[i]);
            if (unlikely(fact.get() == nullptr)) {
                std::ostringstream message;
                message << "Error parsing fact " << i << " of "
                    << polish_facts.size();
                error_log.push_back(message.str());
                error = true;
                continue;
            }
            if (unlikely(not is_fact(* fact))) {
                std::ostringstream message;
                message << "Error: fact " << i << " of " << polish_facts.size()
                    << " is not a relation";
                error_log.push_back(message.str());
                error = true;
                continue;
            }
            facts.push_back(fact);
        }
        if (error) return Theory();
    }

    std::vector<const Expr *> exprs;
    for (auto expr_ptr : deduped) {
        exprs.push_back(expr_ptr.get());
    }

    return {std::move(facts), std::move(exprs)};
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
    const Expr * expr,
    const std::unordered_map<const Expr *, State> & states,
    std::unordered_map<const Expr *, std::vector<State>> & message_queues,
    Approximator & approximator)
{
    const std::string & name = expr->name;
    switch (expr->arity) {
        case NULLARY_FUNCTION: {
            const Expr * val = expr;
            message_queues[val].push_back(approximator.nullary_function(name));
        } break;

        case INJECTIVE_FUNCTION: {
            if (name == "QUOTE") break; // QUOTE is not monotone
            TODO("propagate injective_function " << name);
        } break;

        case BINARY_FUNCTION:
        case SYMMETRIC_FUNCTION: {
            const Expr * lhs = expr->args[0].get();
            const Expr * rhs = expr->args[1].get();
            const Expr * val = expr;
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
            const Expr * lhs = expr->args[0].get();
            const Expr * rhs = expr->args[1].get();
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
            const Expr * lhs = expr->args[0].get();
            const Expr * rhs = expr->args[1].get();
            message_queues[lhs].push_back(map_find(states, rhs));
            message_queues[rhs].push_back(map_find(states, lhs));
        } break;

        case HOLE: break; // no information
        case VAR: break; // no information
    }
}

// this should have time complexity O(#constraints)
inline size_t propagate_step (
    std::unordered_map<const Expr *, State> & states,
    std::unordered_map<const Expr *, std::vector<State>> & message_queues,
    const Theory & theory,
    Approximator & approximator)
{
    for (const Expr * expr : theory.exprs) {
        propagate_constraint(expr, states, message_queues, approximator);
    }

    size_t change_count = 0;
    for (auto & i : states) {
        const Expr * expr = i.first;
        State & state = i.second;
        std::vector<State> & messages = message_queues.find(expr)->second;
        const State updated_state = approximator.lazy_fuse(messages);
        messages.clear();
        if (updated_state != state) {
            POMAGMA_ASSERT1(
                approximator.expensive_refines(updated_state, state),
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
    POMAGMA_DEBUG("Propagating " << theory.exprs.size() << " variables");

    std::unordered_map<const Expr *, State> states;
    for (const Expr * expr : theory.exprs) {
        states.insert({expr, approximator.unknown()});
    }

    std::unordered_map<const Expr *, std::vector<State>> message_queues;
    while (propagate_step(states, message_queues, theory, approximator)) {}

    Trool is_valid = Trool::TRUE;
    for (const auto & i : states) {
        is_valid = and_trool(is_valid, approximator.lazy_is_valid(i.second));
    }
    return is_valid;
}

} // namespace propagate
} // namespace pomagma
