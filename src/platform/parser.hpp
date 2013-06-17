#pragma once

#include "util.hpp"
#include "signature.hpp"
#include <tuple>

namespace pomagma
{

template<class Reducer>
class Parser
{
public:

    // Parser agrees not to touch reducer until after construction
    Parser (Signature & signature, Reducer & reducer)
        : m_signature(signature),
          m_reducer(reducer)
    {
    }

    void begin (const std::string & expression)
    {
        m_stream.str(expression);
    }

    std::string parse_token ()
    {
        std::string token;
        POMAGMA_ASSERT(std::getline(m_stream, token, ' '),
            "expression terminated prematurely: " << m_stream);
        return token;
    }

    typedef typename Reducer::Term Term;
    Term parse_term ()
    {
        std::string token = parse_token();
        if (const auto * fun = m_signature.nullary_functions(token)) {
            return m_reducer.reduce(token, fun);
        } else if (const auto * fun = m_signature.injective_functions(token)) {
            Term key = parse_term();
            return m_reducer.reduce(token, fun, key);
        } else if (const auto * fun = m_signature.binary_functions(token)) {
            Term lhs = parse_term();
            Term rhs = parse_term();
            return m_reducer.reduce(token, fun, lhs, rhs);
        } else if (const auto * fun = m_signature.symmetric_functions(token)) {
            Term lhs = parse_term();
            Term rhs = parse_term();
            return m_reducer.reduce(token, fun, lhs, rhs);
        } else {
            POMAGMA_ERROR("unrecognized token: " << token);
            return 0;
        }
    }

    void end ()
    {
        POMAGMA_ASSERT(m_stream.eof(), "unexpected tokens in: " << m_stream);
    }

private:

    Signature & m_signature;
    Reducer & m_reducer;
    std::istringstream m_stream;
};


class OldParser : noncopyable
{
public:

    OldParser (Signature & signature) : m_signature(signature) {}

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

    //Ob parse_term (const std::string & term)
    //{
    //}

protected:

    virtual Ob check_insert (const NullaryFunction * fun) = 0;
    virtual Ob check_insert (const InjectiveFunction * fun, Ob key) = 0;
    virtual Ob check_insert (const BinaryFunction * fun, Ob lhs, Ob rhs) = 0;
    virtual Ob check_insert (const SymmetricFunction * fun, Ob lhs, Ob rhs) = 0;

private:

    Signature & m_signature;
};

} // namespace pomagma
