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

    const Term * get_nullary_function (
            const std::string & name)
    {
        return get(Term(Term::NULLARY_FUNCTION, name));
    }
    const Term * get_injective_function (
            const std::string & name,
            const Term * arg)
    {
        return get(Term(Term::INJECTIVE_FUNCTION, name, arg));
    }
    const Term * get_binary_function (
            const std::string & name,
            const Term * lhs,
            const Term * rhs)
    {
        return get(Term(Term::BINARY_FUNCTION, name, lhs, rhs));
    }
    const Term * get_symmetric_function (
            const std::string & name,
            const Term * lhs,
            const Term * rhs)
    {
        if (lhs > rhs) {
            std::swap(lhs, rhs);
        }
        return get(Term(Term::SYMMETRIC_FUNCTION, name, lhs, rhs));
    }
    const Term * get_binary_relation (
            const std::string & name,
            const Term * lhs,
            const Term * rhs)
    {
        return get(Term(Term::BINARY_RELATION, name, lhs, rhs));
    }
    const Term * get_variable (
            const std::string & name)
    {
        return get(Term(Term::VARIABLE, name));
    }

    void clear () { m_terms.clear(); }

private:

    const Term * get (Term && key) { return & * m_terms.insert(key).first; }

    std::unordered_set<Term, Term::Hash, Term::Equal> m_terms;
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
