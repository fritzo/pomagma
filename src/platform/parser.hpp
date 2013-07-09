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
        m_stream.clear();
    }

    std::string parse_token ()
    {
        std::string token;
        POMAGMA_ASSERT(std::getline(m_stream, token, ' '),
            "expression terminated prematurely: " << m_stream.str());
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
            POMAGMA_ERROR(
                "unrecognized token '" << token << "' in:" << m_stream.str());
            return Term();
        }
    }

    void end ()
    {
        std::string token;
        POMAGMA_ASSERT(not std::getline(m_stream, token, ' '),
            "unexpected token '" << token << "' in: " << m_stream.str());
    }

private:

    Signature & m_signature;
    Reducer & m_reducer;
    std::istringstream m_stream;
};


class LineParser
{
public:

    LineParser (const char * filename)
        : m_file(filename)
    {
        POMAGMA_ASSERT(m_file, "failed to open " << filename);
        next();
    }

    bool ok () const { return not m_line.empty(); }

    const std::string & operator* () const { return m_line; }

    void next ()
    {
        while (std::getline(m_file, m_line)) {
            if (not m_line.empty() and m_line[0] != '#') {
                return;
            }
        }
        m_line.clear();
    }

private:

    std::ifstream m_file;
    std::string m_line;
};


} // namespace pomagma
