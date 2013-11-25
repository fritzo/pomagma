#include "corpus.hpp"
#include <pomagma/platform/hash_map.hpp>
#include <unordered_set>

namespace pomagma
{

class Corpus
{
public:

    struct Term
    {
        enum Arity {
            NULLARY_FUNCTION,
            INJECTIVE_FUNCTION,
            BINARY_FUNCTION,
            SYMMETRIC_FUNCTION,
            BINARY_RELATION,
            VARIABLE
        };

        struct Equal
        {
            bool operator() (const Term & x, const Term & y) const
            {
                return x.arity == y.arity
                   and x.name == y.name
                   and x.arg0 == y.arg0
                   and x.arg1 == y.arg1;
            }
        };

        struct Hash
        {
            std::hash<std::string> hash_string;
            std::hash<const Term *> hash_pointer;

            uint64_t operator() (const Term & x) const
            {
                FNV_hash::HashState state;
                state.add(x.arity);
                state.add(hash_string(x.name));
                state.add(hash_pointer(x.arg0));
                state.add(hash_pointer(x.arg1));
                return state.get();
            }
        };

        Term () {}
        Term (
                Arity a,
                const std::string & n,
                const Term * a0 = nullptr,
                const Term * a1 = nullptr)
            : arity(a), name(n), arg0(a0), arg1(a1)
        {}

        Arity arity;
        std::string name;
        const Term * arg0;
        const Term * arg1;
    };

    Corpus () {}

    const Term * nullary_function (
            const std::string & name)
    {
        return get(Term(Term::NULLARY_FUNCTION, name));
    }
    const Term * injective_function (
            const std::string & name,
            const Term * arg)
    {
        return get(Term(Term::INJECTIVE_FUNCTION, name, arg));
    }
    const Term * binary_function (
            const std::string & name,
            const Term * lhs,
            const Term * rhs)
    {
        return get(Term(Term::BINARY_FUNCTION, name, lhs, rhs));
    }
    const Term * symmetric_function (
            const std::string & name,
            const Term * lhs,
            const Term * rhs)
    {
        if (lhs > rhs) {
            std::swap(lhs, rhs);
        }
        return get(Term(Term::SYMMETRIC_FUNCTION, name, lhs, rhs));
    }
    const Term * binary_relation (
            const std::string & name,
            const Term * lhs,
            const Term * rhs)
    {
        return get(Term(Term::BINARY_RELATION, name, lhs, rhs));
    }
    const Term * variable (
            const std::string & name)
    {
        return get(Term(Term::VARIABLE, name));
    }

    void clear () { m_terms.clear(); }

    class Parser;

private:

    const Term * get (Term && key) { return & * m_terms.insert(key).first; }

    std::unordered_set<Term, Term::Hash, Term::Equal> m_terms;
};

class Corpus::Parser
{
public:

    Parser (Signature & signature, Corpus & corpus)
        : m_signature(signature),
          m_corpus(corpus)
    {
    }

    const Term * parse (const std::string & expression)
    {
        begin(expression);
        const Term * result = parse_term();
        end();
        return result;
    }

private:

    void begin (const std::string & expression)
    {
        m_stream.str(expression);
        m_stream.clear();
    }

    std::string parse_token ()
    {
        std::string token;
        if (not std::getline(m_stream, token, ' ')) {
            POMAGMA_WARN(
                "expression terminated prematurely: " << m_stream.str());
        }
        return token;
    }

    const Term * parse_term ()
    {
        std::string name = parse_token();
        if (m_signature.nullary_function(name)) {
            return m_corpus.nullary_function(name);
        } else if (m_signature.injective_function(name)) {
            const Term * key = parse_term();
            return m_corpus.injective_function(name, key);
        } else if (m_signature.binary_function(name)) {
            const Term * lhs = parse_term();
            const Term * rhs = parse_term();
            return m_corpus.binary_function(name, lhs, rhs);
        } else if (m_signature.symmetric_function(name)) {
            const Term * lhs = parse_term();
            const Term * rhs = parse_term();
            return m_corpus.symmetric_function(name, lhs, rhs);
        } else if (m_signature.binary_relation(name)) {
            const Term * lhs = parse_term();
            const Term * rhs = parse_term();
            return m_corpus.binary_relation(name, lhs, rhs);
        } else {
            return m_corpus.variable(name);
        }
    }

    void end ()
    {
        std::string token;
        if (std::getline(m_stream, token, ' ')) {
            POMAGMA_WARN(
                "unexpected token '" << token << "' in: " << m_stream.str());
        }
    }

    Signature & m_signature;
    Corpus & m_corpus;
    std::istringstream m_stream;
};

class CorpusApproximation::Guts
{
public:

    Guts ();

    typedef size_t Id;
    std::atomic<uint_fast64_t> m_id_generator;
    size_t new_id () { return m_id_generator++; }

    std::unordered_map<Id, Approximation *> m_approximations;
    std::unordered_map<std::string, Id> m_definitions;
};

CorpusApproximation::Guts::Guts ()
    : m_id_generator(0)
{
}

} // namespace pomagma
