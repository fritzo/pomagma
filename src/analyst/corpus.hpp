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
                   and x.arg1 == y.arg1
                   and x.ob == y.ob;
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
                state.add(x.ob);
                return state.get();
            }
        };

        Term () {}
        Term (Ob o) : arity(OB), name(), arg0(nullptr), arg1(nullptr), ob(o) {}
        Term (
                Arity a,
                const std::string & n,
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

    struct Line
    {
        std::string maybe_name;
        std::string code;
    };

    struct Diff
    {
        std::vector<const Term *> removed;
        std::vector<const Term *> added;
        std::vector<const Term *> lines;
    };

    Corpus (Signature & signature);
    ~Corpus ();

    Diff update (
            const std::vector<Line> & lines,
            std::vector<std::string> & error_log);

private:

    class Dag;
    class Parser;

    Dag & m_dag;
    Parser & m_parser;
    std::unordered_map<std::string, const Term *> m_definitions;
};

} // namespace pomagma
