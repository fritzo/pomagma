#include "corpus.hpp"
#include <unordered_set>
#include <map>

namespace pomagma
{

class Corpus::Dag
{
public:

    typedef size_t Id;

    Dag (Signature & signature);
    ~Dag ();

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

    const Term * link (const Term * term, size_t depth);

    class Linker
    {
    public:
        Linker (Dag & dag);
        ~Linker ();
        void operator() (const std::string & name, const Term * term);
    private:
        Dag & m_dag;
        std::unordered_map<std::string, const Term *> m_definitions;
    };

    class GarbageCollector
    {
    public:
        GarbageCollector (Dag & dag);
        ~GarbageCollector ();
        void operator() (const Term * term);
    private:
        Dag & m_dag;
        std::unordered_set<const Term *> m_used;
    };

private:

    const Term * get (Term && key)
    {
        * m_new_term.first = key;
        auto pair = m_terms.insert(m_new_term);
        if (pair.second) {
            m_ranked.insert(
                std::make_pair(m_new_term.second, m_new_term.first));
            m_new_term.first = new Term();
            m_new_term.second += 1;
        }
        return pair.first->first;
    }

    Signature & m_signature;
    std::pair<Term *, Id> m_new_term;
    std::unordered_map<Term *, Id, Term::Hash, Term::Equal> m_terms;
    std::map<Id, const Term *> m_ranked;
    std::unordered_map<std::string, const Term *> m_definitions;
};

Corpus::Dag::Dag (Signature & signature)
    : m_signature(signature),
      m_new_term(std::make_pair(new Term(), 0))
{
}

Corpus::Dag::~Dag ()
{
    POMAGMA_ASSERT_EQ(m_ranked.size(), m_terms.size());
    delete m_new_term.first;
    for (auto pair : m_terms) {
        delete pair.first;
    }
}

const Corpus::Term * Corpus::Dag::link (const Term * term, size_t depth)
{
    switch (term->arity) {
        case Term::OB:
        case Term::HOLE:
        case Term::NULLARY_FUNCTION:
            return term;

        case Term::INJECTIVE_FUNCTION:
            return injective_function(term->name, link(term->arg0, depth));

        case Term::BINARY_FUNCTION:
            return binary_function(
                term->name,
                link(term->arg0, depth),
                link(term->arg1, depth));

        case Term::SYMMETRIC_FUNCTION:
            return symmetric_function(
                term->name,
                link(term->arg0, depth),
                link(term->arg1, depth));

        case Term::BINARY_RELATION:
            return binary_relation(
                term->name,
                link(term->arg0, depth),
                link(term->arg1, depth));

        case Term::VARIABLE:
            if (depth == 0) {
                return hole();
            } else {
                return link(m_definitions[term->name], depth - 1);
            }
    }

    return nullptr; // never reached
}

Corpus::Dag::Linker::Linker (Dag & dag)
    : m_dag(dag)
{
    POMAGMA_ASSERT_EQ(m_dag.m_ranked.size(), m_dag.m_terms.size());
    m_dag.m_definitions.clear();
    const Term * hole = m_dag.hole();

    for (auto pair : m_dag.m_terms) {
        const Term * term = pair.first;
        if (term->arity == Term::VARIABLE) {
            m_definitions.insert(std::make_pair(term->name, hole));
        }
    }
}

inline void Corpus::Dag::Linker::operator() (
        const std::string & name,
        const Term * term)
{
    m_definitions[name] = term;
}

Corpus::Dag::Linker::~Linker ()
{
    TODO("get references of defined terms");

    std::vector<std::string> index_to_name;
    std::unordered_map<std::string, size_t> name_to_index;
    for (auto pair : m_definitions) {
        name_to_index[pair.first] = index_to_name.size();
        index_to_name.push_back(pair.first);
    }

    std::unordered_set<const Term *> closed;
    auto is_closed = [&](const Term * term) {
        return closed.find(term) != closed.end();
    };
    // this loop has worst-case time complexity m_ranked.size() * name_count
    bool changed = true;
    while (changed) {
        changed = false;
        for (auto pair : m_dag.m_ranked) {
            const Term * term = pair.second;
            if (not is_closed(term)) {
                switch (term->arity) {
                    case Term::OB:
                    case Term::HOLE:
                    case Term::NULLARY_FUNCTION:
                        closed.insert(term);
                        break;

                    case Term::INJECTIVE_FUNCTION:
                        if (is_closed(term->arg0)) {
                            closed.insert(term);
                        }
                        break;

                    case Term::BINARY_FUNCTION:
                    case Term::SYMMETRIC_FUNCTION:
                    case Term::BINARY_RELATION:
                        if (is_closed(term->arg0) and is_closed(term->arg1)) {
                            closed.insert(term);
                        }
                        break;

                    case Term::VARIABLE:
                        if (is_closed(m_definitions[term->name])) {
                            closed.insert(term);
                            changed = true;
                        }
                        break;
                }
            }
        }
    }

    TODO("define well-founded terms in order of increasing rank");
}

Corpus::Dag::GarbageCollector::GarbageCollector (Dag & dag)
    : m_dag(dag)
{
}

inline void Corpus::Dag::GarbageCollector::operator() (const Term * term)
{
    m_used.insert(term);
}

Corpus::Dag::GarbageCollector::~GarbageCollector ()
{
    POMAGMA_ASSERT_EQ(m_dag.m_ranked.size(), m_dag.m_terms.size());
    TODO("collect garbage");
    POMAGMA_ASSERT_EQ(m_dag.m_ranked.size(), m_dag.m_terms.size());
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

    TODO("warn about missing definitions");

    // first do a linker pass
    {
        Dag::Linker define(m_dag);
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
        Dag::GarbageCollector mark_used(m_dag);
        for (const auto & line : lines) {
            const Term * term = m_parser.parse(line.code);
            diff.lines.push_back(term);
            mark_used(term);
        }
    }

    TODO("compute removed, added");

    if (not error_log.empty()) {
        POMAGMA_WARN("found " << error_log.size() << " errors");
    }
    return diff;
}

} // namespace pomagma
