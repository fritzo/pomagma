#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/analyst/approximate.hpp>
#include <pomagma/platform/hash_map.hpp>

namespace pomagma
{

class Corpus
{
public:

    struct Term
    {
        enum Arity {
            OB,
            HOLE,
            NULLARY_FUNCTION,
            INJECTIVE_FUNCTION,
            BINARY_FUNCTION,
            SYMMETRIC_FUNCTION,
            BINARY_RELATION,
            VARIABLE  // must be last to match CachedApproximator::Term::Arity
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
                state.add(x.ob);
                return state.get();
            }
        };

        bool operator== (const Term & o) const
        {
            return arity == o.arity
               and name == o.name
               and arg0 == o.arg0
               and arg1 == o.arg1
               and ob == o.ob;
        }
        bool operator!= (const Term & o) const { return not operator==(o); }

        Term () {}
        Term (Ob o)
            : arity(OB), name(), arg0(nullptr), arg1(nullptr), ob(o)
        {}
        Term (
                Arity a,
                const std::string & n = "",
                const Term * a0 = nullptr,
                const Term * a1 = nullptr)
            : arity(a), name(n), arg0(a0), arg1(a1), ob(0)
        {}

        Arity arity;
        std::string name;
        const Term * arg0;
        const Term * arg1;
        Ob ob;
    };

    template<class T>
    struct LineOf
    {
        std::string maybe_name;
        T body;

        bool is_definition () const { return not maybe_name.empty(); }
        bool is_assertion () const { return maybe_name.empty(); }
    };

    Corpus (Signature & signature);
    ~Corpus ();

    std::vector<LineOf<const Term *>> parse (
            const std::vector<LineOf<std::string>> & lines,
            std::vector<std::string> & error_log);

private:

    class Dag;
    class Parser;
    class Linker;

    Dag & m_dag;
    Parser & m_parser;
};

} // namespace pomagma
