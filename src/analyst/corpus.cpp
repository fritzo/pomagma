#include "corpus.hpp"
#include <unordered_set>

namespace pomagma
{

class Corpus::Dag
{
public:

    Dag (Signature & signature) : m_signature(signature) {}

    const Term * truthy () { return nullary_function("I"); }
    const Term * falsey () { return nullary_function("BOT"); }

    const Term * hole ()
    {
        return get(Term(Term::HOLE));
    }
    const Term * variable (
            const std::string & name)
    {
        auto i = m_definitions.find(name);
        if (i == m_definitions.end()) {
            return get(Term(Term::VARIABLE, name));
        } else {
            return i->second;
        }
    }
    const Term * nullary_function (
            const std::string & name)
    {
        if (auto * fun = m_signature.nullary_function(name)) {
            if (Ob ob = fun->find()) {
                return get(Term(ob));
            }
        }
        return get(Term(Term::NULLARY_FUNCTION, name));
    }
    const Term * injective_function (
            const std::string & name,
            const Term * arg)
    {
        if (arg->ob) {
            if (auto * fun = m_signature.injective_function(name)) {
                if (Ob ob = fun->find(arg->ob)) {
                    return get(Term(ob));
                }
            }
        }
        return get(Term(Term::INJECTIVE_FUNCTION, name, arg));
    }
    const Term * binary_function (
            const std::string & name,
            const Term * lhs,
            const Term * rhs)
    {
        if (lhs->ob and rhs->ob) {
            if (auto * fun = m_signature.binary_function(name)) {
                if (Ob ob = fun->find(lhs->ob, rhs->ob)) {
                    return get(Term(ob));
                }
            }
        }
        return get(Term(Term::BINARY_FUNCTION, name, lhs, rhs));
    }
    const Term * symmetric_function (
            const std::string & name,
            const Term * lhs,
            const Term * rhs)
    {
        if (lhs->ob and rhs->ob) {
            if (auto * fun = m_signature.symmetric_function(name)) {
                if (Ob ob = fun->find(lhs->ob, rhs->ob)) {
                    return get(Term(ob));
                }
            }
        }
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
        if (lhs->ob and rhs->ob) {
            if (auto * rel = m_signature.binary_relation(name)) {
                if (rel->find(lhs->ob, rhs->ob)) {
                    return truthy();
                }
            }
            std::string negated = m_signature.negate(name);
            if (auto * rel = m_signature.binary_relation(negated)) {
                if (rel->find(lhs->ob, rhs->ob)) {
                    return falsey();
                }
            }
        }
        return get(Term(Term::BINARY_RELATION, name, lhs, rhs));
    }

    class Linker
    {
    public:
        Linker (Dag & dag, std::vector<std::string> & error_log)
            : m_dag(dag),
              m_error_log(error_log)
        {
            m_dag.m_definitions.clear();
        }
        ~Linker ();
        void operator() (const std::string & name, const Term * term);
    private:
        Dag & m_dag;
        std::vector<std::string> & m_error_log;
        std::unordered_map<std::string, const Term *> m_definitions;
    };
    Linker linker (std::vector<std::string> & error_log)
    {
        return Linker(* this, error_log);
    }

    class GarbageCollector
    {
    public:
        GarbageCollector (Dag & dag) : m_dag(dag) {}
        ~GarbageCollector ();
        void operator() (const Term * term);
    private:
        Dag & m_dag;
        std::unordered_set<const Term *> m_used;
    };
    GarbageCollector garbage_collector () { return GarbageCollector(* this); }

private:

    const Term * get (Term && key) { return & * m_terms.insert(key).first; }
    std::unordered_map<std::string, size_t> get_ranks ();

    Signature & m_signature;
    std::unordered_set<Term, Term::Hash, Term::Equal> m_terms;
    std::unordered_map<std::string, const Term *> m_definitions;
};

std::unordered_map<std::string, size_t> Corpus::Dag::get_ranks ()
{
    TODO("compute ranks");
    //std::unordered_map<const Term *, DenseSet *> vars;
    std::unordered_map<std::string, size_t> ranks;
    return ranks;
}

void Corpus::Dag::Linker::operator() (
        const std::string & name,
        const Term * term)
{
    auto pair = m_definitions.insert(std::make_pair(name, term));
    if (not pair.second) {
        m_error_log.push_back("duplicate defintion: " + name);
    }
}

Corpus::Dag::Linker::~Linker ()
{
    TODO("warn about missing definitions");
    TODO("get references of defined terms");
    TODO("compute ranks");
    TODO("define well-founded terms in order of increasing rank");
}

void Corpus::Dag::GarbageCollector::operator() (const Term * term)
{
    m_used.insert(term);
}

Corpus::Dag::GarbageCollector::~GarbageCollector ()
{
    TODO("collect garbage");
}

class Corpus::Parser
{
public:

    Parser (Signature & signature, Corpus::Dag & dag)
        : m_signature(signature),
          m_dag(dag)
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
            return m_dag.nullary_function(name);
        } else if (m_signature.injective_function(name)) {
            const Term * key = parse_term();
            return m_dag.injective_function(name, key);
        } else if (m_signature.binary_function(name)) {
            const Term * lhs = parse_term();
            const Term * rhs = parse_term();
            return m_dag.binary_function(name, lhs, rhs);
        } else if (m_signature.symmetric_function(name)) {
            const Term * lhs = parse_term();
            const Term * rhs = parse_term();
            return m_dag.symmetric_function(name, lhs, rhs);
        } else if (m_signature.binary_relation(name)) {
            const Term * lhs = parse_term();
            const Term * rhs = parse_term();
            return m_dag.binary_relation(name, lhs, rhs);
        } else if (name == "HOLE") {
            return m_dag.hole();
        } else {
            return m_dag.variable(name);
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
    Dag & m_dag;
    std::istringstream m_stream;
};


Corpus::Corpus (Signature & signature)
    : m_dag(* new Dag(signature)),
      m_parser(* new Parser(signature, m_dag))
{
}

Corpus::~Corpus ()
{
    delete & m_parser;
    delete & m_dag;
}

Corpus::Diff Corpus::update (
        const std::vector<Corpus::Line> & lines,
        std::vector<std::string> & error_log)
{
    // TODO do two parser passes and run dag linker as follows:
    // parse_all_terms();
    // dag.link();
    // parse_all_terms();
    // compute_diff);
    // dag.garbage_collect();

    // first do a linker pass
    {
        auto define = m_dag.linker(error_log);
        for (const auto & line : lines) {
            if (line.is_definition()) {
                const std::string & name = line.maybe_name;
                const Term * term = m_parser.parse(line.code);
                define(name, term);
            }
        }
    }

    // then do a maximally-linked pass
    Diff diff;
    {
        auto mark_used = m_dag.garbage_collector();
        for (const auto & line : lines) {
            const Term * term = m_parser.parse(line.code);
            diff.lines.push_back(term);
            mark_used(term);
        }
    }

    TODO("compute removed, added");
    return diff;
}

} // namespace pomagma
