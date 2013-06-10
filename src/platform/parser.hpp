#pragma once

#include "util.hpp"
#include "signature.hpp"

namespace pomagma
{

class Parser : noncopyable
{
public:

    Parser (Signature & signature) : m_signature(signature) {}

    Ob parse (std::istringstream & stream)
    {
        std::string token;
        POMAGMA_ASSERT(std::getline(stream, token, ' '),
                "expression terminated prematurely");

        if (const auto * fun = m_signature.nullary_functions(token)) {
            return check_insert(fun);
        } else if (const auto * fun = m_signature.injective_functions(token)) {
            Ob key = parse(stream);
            return key ? check_insert(fun, key) : 0;
        } else if (const auto * fun = m_signature.binary_functions(token)) {
            Ob lhs = parse(stream);
            Ob rhs = parse(stream);
            return lhs and rhs ? check_insert(fun, lhs, rhs) : 0;
        } else if (const auto * fun = m_signature.symmetric_functions(token)) {
            Ob lhs = parse(stream);
            Ob rhs = parse(stream);
            return lhs and rhs ? check_insert(fun, lhs, rhs) : 0;
        } else {
            POMAGMA_ERROR("unrecognized token: " << token);
            return 0;
        }
    }

protected:

    virtual Ob check_insert (const NullaryFunction * fun) = 0;
    virtual Ob check_insert (const InjectiveFunction * fun, Ob key) = 0;
    virtual Ob check_insert (const BinaryFunction * fun, Ob lhs, Ob rhs) = 0;
    virtual Ob check_insert (const SymmetricFunction * fun, Ob lhs, Ob rhs) = 0;

private:

    Signature & m_signature;
};

} // namespace pomagma
