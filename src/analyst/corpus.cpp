#include "corpus.hpp"
#include <pomagma/platform/hash_map.hpp>

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

        Arity arity;
        std::string name;
        const Term * arg0;
        const Term * arg1;
    };

    Corpus () {}
    ~Corpus () { clear(); }

    const Term & get_nullary_function (
            const std::string & name)
    {
        Term key = {Term::NULLARY_FUNCTION, name, nullptr, nullptr};
        return get(key);
    }
    const Term & get_injective_function (
            const std::string & name,
            const Term & arg)
    {
        Term key = {Term::INJECTIVE_FUNCTION, name, & arg, nullptr};
        return get(key);
    }
    const Term & get_binary_function (
            const std::string & name,
            const Term & lhs,
            const Term & rhs)
    {
        Term key = {Term::BINARY_FUNCTION, name, & lhs, & rhs};
        return get(key);
    }
    const Term & get_symmetric_function (
            const std::string & name,
            const Term & lhs,
            const Term & rhs)
    {
        const Term * arg0 = & lhs;
        const Term * arg1 = & rhs;
        if (arg0 > arg1) {
            std::swap(arg0, arg1);
        }
        Term key = {Term::SYMMETRIC_FUNCTION, name, arg0, arg1};
        return get(key);
    }
    const Term & get_binary_relation (
            const std::string & name,
            const Term & lhs,
            const Term & rhs)
    {
        Term key = {Term::BINARY_RELATION, name, & lhs, & rhs};
        return get(key);
    }
    const Term & get_variable (
            const std::string & name)
    {
        Term key = {Term::VARIABLE, name, nullptr, nullptr};
        return get(key);
    }

    void clear ()
    {
        for (auto & pair : m_terms) {
            delete pair.second;
        }
    }

private:

    const Term & get (const Term & key)
    {
        auto pair = m_terms.insert(std::make_pair(key, nullptr));
        if (pair.second) {
            pair.first->second = new Term(key);
        }
        return * pair.first->second;
    }

    std::unordered_map<Term, Term *, Term::Hash, Term::Equal> m_terms;
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
