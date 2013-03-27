#pragma once

#include "parser.hpp"
#include "signature.hpp"

namespace pomagma
{

Parser::Parser (Signature & signature)
    : m_signature(signature)
{
}

Ob Parser::parse_insert (std::istringstream & stream, Policy & policy) const
{
    std::string token;
    POMAGMA_ASSERT(std::getline(stream, token, ' '),
            "expression terminated prematurely");

    if (const auto * fun = m_signature.nullary_functions(token)) {
        return policy.check_insert(fun);
    } else if (const auto * fun = m_signature.injective_functions(token)) {
        Ob key = parse_insert(stream, policy);
        return key ? policy.check_insert(fun, key) : 0;
    } else if (const auto * fun = m_signature.binary_functions(token)) {
        Ob lhs = parse_insert(stream, policy);
        Ob rhs = parse_insert(stream, policy);
        return lhs and rhs ? policy.check_insert(fun, lhs, rhs) : 0;
    } else if (const auto * fun = m_signature.symmetric_functions(token)) {
        Ob lhs = parse_insert(stream, policy);
        Ob rhs = parse_insert(stream, policy);
        return lhs and rhs ? policy.check_insert(fun, lhs, rhs) : 0;
    } else {
        POMAGMA_ERROR("bad token: " << token);
        return 0;
    }
}

} // namespace pomagma
