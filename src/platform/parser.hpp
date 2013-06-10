#pragma once

#include "util.hpp"
#include "signature.hpp"

namespace pomagma
{

// TODO get CRTP working
class Parser : noncopyable
{
public:

    Parser (Signature & signature) : m_signature(signature) {}

    template<class Policy>
    Ob parse (std::istringstream & stream, Policy * policy)
    {
        std::string token;
        POMAGMA_ASSERT(std::getline(stream, token, ' '),
                "expression terminated prematurely");

        if (const auto * fun = m_signature.nullary_functions(token)) {
            return policy->check_insert(fun);
        } else if (const auto * fun = m_signature.injective_functions(token)) {
            Ob key = parse(stream, policy);
            return key ? policy->check_insert(fun, key) : 0;
        } else if (const auto * fun = m_signature.binary_functions(token)) {
            Ob lhs = parse(stream, policy);
            Ob rhs = parse(stream, policy);
            return lhs and rhs ? policy->check_insert(fun, lhs, rhs) : 0;
        } else if (const auto * fun = m_signature.symmetric_functions(token)) {
            Ob lhs = parse(stream, policy);
            Ob rhs = parse(stream, policy);
            return lhs and rhs ? policy->check_insert(fun, lhs, rhs) : 0;
        } else {
            POMAGMA_ERROR("unrecognized token: " << token);
            return 0;
        }
    }

private:

    Signature & m_signature;
};

} // namespace pomagma
