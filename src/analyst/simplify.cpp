#include <pomagma/analyst/simplify.hpp>

namespace pomagma
{

Simplifier::Simplifier (
        Signature & signature,
        const std::vector<std::string> & routes,
        std::vector<std::string> & error_log)
    : m_signature(signature),
      m_nless(* signature.binary_relation("NLESS")),
      m_routes(routes),
      m_error_log(error_log)
{
    POMAGMA_ASSERT(&m_nless != nullptr, "NLESS is not defined");
}

inline Simplifier::Term Simplifier::reduce (
        const std::string & token,
        const NullaryFunction * fun)
{
    Term val;
    val.ob = fun->find();
    val.route = val.ob ? m_routes[val.ob] : token;
    return val;
}

inline Simplifier::Term Simplifier::reduce (
        const std::string & token,
        const InjectiveFunction * fun,
        const Term & key)
{
    Term val;
    val.ob = key.ob ? fun->find(key.ob) : 0;
    val.route = val.ob ? m_routes[val.ob] : token + " " + key.route;
    return val;
}

inline Simplifier::Term Simplifier::reduce (
        const std::string & token,
        const BinaryFunction * fun,
        const Term & lhs,
        const Term & rhs)
{
    Term val;
    val.ob = lhs.ob and rhs.ob ? fun->find(lhs.ob, rhs.ob) : 0;
    val.route = val.ob
              ? m_routes[val.ob]
              : token + " " + lhs.route + " " + rhs.route;
    return val;
}

inline Simplifier::Term Simplifier::reduce (
        const std::string & token,
        const SymmetricFunction * fun,
        const Term & lhs,
        const Term & rhs)
{
    Term val;
    val.ob = lhs.ob and rhs.ob ? fun->find(lhs.ob, rhs.ob) : 0;
    val.route = val.ob
              ? m_routes[val.ob]
              : token + " " + lhs.route + " " + rhs.route;
    return val;
}

inline Simplifier::Term Simplifier::reduce (
        const std::string & token,
        const UnaryRelation * rel,
        const Term & key)
{
    if (key.ob) {
        if (rel->find(key.ob)) {
            return semi_true();
        }
        std::string negated = m_signature.negate(token);
        if (auto * negated_rel = m_signature.unary_relation(negated)) {
            if (negated_rel->find(key.ob)) {
                return semi_false();
            }
        }
    }
    return {0, token + " " + key.route};
}

inline Simplifier::Term Simplifier::reduce (
        const std::string & token,
        const BinaryRelation * rel,
        const Term & lhs,
        const Term & rhs)
{
    if (lhs.ob and rhs.ob) {
        if (rel->find(lhs.ob, rhs.ob)) {
            return semi_true();
        }
        std::string negated = m_signature.negate(token);
        if (auto * negated_rel = m_signature.binary_relation(negated)) {
            if (negated_rel->find(lhs.ob, rhs.ob)) {
                return semi_false();
            }
        }
    }
    return {0, token + " " + lhs.route + " " + rhs.route};
}

inline Simplifier::Term Simplifier::reduce_equal (
        const Term & lhs,
        const Term & rhs)
{
    if (lhs.ob and rhs.ob) {
        if (lhs.ob == rhs.ob) {
            return semi_true();
        }
        if (m_nless.find(lhs.ob, rhs.ob) or m_nless.find(rhs.ob, lhs.ob)) {
            return semi_false();
        }
    }
    if (lhs.route == rhs.route) {
        return semi_true();
    }
    return {0, "EQUAL " + lhs.route + " " + rhs.route};
}

#define POMAGMA_PARSER_WARN(ARG_message)\
{\
    std::ostringstream message;\
    message << ARG_message;\
    m_error_log.push_back(message.str());\
    POMAGMA_WARN(message.str());\
}

inline void Simplifier::begin (const std::string & expression)
{
    m_stream.str(expression);
    m_stream.clear();
}

inline std::string Simplifier::parse_token ()
{
    std::string token;
    if (not std::getline(m_stream, token, ' ')) {
        POMAGMA_PARSER_WARN(
            "expression terminated prematurely: " << m_stream.str());
    }
    return token;
}

Simplifier::Term Simplifier::parse_term ()
{
    std::string token = parse_token();
    if (const auto * fun = m_signature.nullary_function(token)) {
        return reduce(token, fun);
    } else if (const auto * fun = m_signature.injective_function(token)) {
        Term key = parse_term();
        return reduce(token, fun, key);
    } else if (const auto * fun = m_signature.binary_function(token)) {
        Term lhs = parse_term();
        Term rhs = parse_term();
        return reduce(token, fun, lhs, rhs);
    } else if (const auto * fun = m_signature.symmetric_function(token)) {
        Term lhs = parse_term();
        Term rhs = parse_term();
        return reduce(token, fun, lhs, rhs);
    } else if (const auto * rel = m_signature.unary_relation(token)) {
        Term arg = parse_term();
        return reduce(token, rel, arg);
    } else if (const auto * rel = m_signature.binary_relation(token)) {
        Term lhs = parse_term();
        Term rhs = parse_term();
        return reduce(token, rel, lhs, rhs);
    } else if (token == "EQUAL") {
        Term lhs = parse_term();
        Term rhs = parse_term();
        return reduce_equal(lhs, rhs);
    } else if (token == "HOLE") {
        return {0, token};
    } else if (token == "VAR") {
        std::string name = parse_token();
        return {0, token + " " + name};
    } else {
        POMAGMA_PARSER_WARN(
            "unrecognized token '" << token << "' in: " << m_stream.str());
        return {0, token};
    }
}

inline void Simplifier::end ()
{
    std::string token;
    if (std::getline(m_stream, token, ' ')) {
        POMAGMA_PARSER_WARN(
            "unexpected token '" << token << "' in: " << m_stream.str());
    }
}

#undef POMAGMA_PARSER_WARN

std::string Simplifier::simplify (const std::string & expression)
{
    begin(expression);
    std::string result = parse_term().route;
    end();
    return result;
}

} // namespace pomagma
