#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/analyst/approximate.hpp>
#include <pomagma/platform/hash_map.hpp>
#include <unordered_set>

namespace pomagma
{

class Corpus
{
    class Dag;
    class Parser;

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

    class Linker
    {
    public:
        const Term * link (const Term * term);
        const Term * approximate (const Term * term, size_t depth);
    private:
        friend class Corpus;
        Linker (Dag & dag, std::vector<std::string> & error_log);
        void define (const std::string & name, const Term * term);
        void finish ();
        const Term * approximate (const Term * term);
        static void accum_free (
                const Term * term,
                std::unordered_set<const Term *> & free);

        Dag & m_dag;
        std::vector<std::string> & m_error_log;
        std::unordered_map<const Term *, const Term *> m_definitions;
        std::unordered_set<const Term *> m_ground_terms;

        size_t m_temp_max_depth;
        std::unordered_map<const Term *, size_t> m_temp_depths;
    };

    Corpus (Signature & signature);
    ~Corpus ();

    Linker linker (
            const std::vector<LineOf<std::string>> & lines,
            std::vector<std::string> & error_log);

    std::vector<LineOf<const Term *>> parse (
            const std::vector<LineOf<std::string>> & lines,
            Linker & linker,
            std::vector<std::string> & error_log);

private:

    Signature & m_signature;
    Dag & m_dag;
};

} // namespace pomagma
