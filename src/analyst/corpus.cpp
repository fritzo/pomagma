#include "corpus.hpp"
#include <unordered_set>
#include <map>

namespace pomagma
{

//----------------------------------------------------------------------------
// Dag

class Corpus::Dag
{
public:

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
        return get(Term(Term::VARIABLE, name));
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

    const std::unordered_set<Term *> & variables () const
    {
        return m_variables;
    }

private:

    const Term * get (Term && key)
    {
        * m_new_term = key;
        auto pair = m_terms.insert(m_new_term);
        if (pair.second) {
            if (m_new_term->arity == Term::VARIABLE) {
                m_variables.insert(m_new_term);
            }
            m_new_term = new Term();
        }
        return * pair.first;
    }

    Signature & m_signature;
    Term * m_new_term;
    std::unordered_set<Term *, Term::Hash, Term::Equal> m_terms;
    std::unordered_set<Term *> m_variables;
};

Corpus::Dag::Dag (Signature & signature)
    : m_signature(signature),
      m_new_term(new Term())
{
}

Corpus::Dag::~Dag ()
{
    delete m_new_term;
    for (Term * term : m_terms) {
        delete term;
    }
}

//----------------------------------------------------------------------------
// Parser

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

//----------------------------------------------------------------------------
// Linker

class Corpus::Linker
{
public:

    Linker (Dag & dag);
    void define (const std::string & name, const Term * term);
    const Term * link (const Term * term, size_t depth);
private:
    const Term * link (const Term * term);

    Dag & m_dag;
    std::unordered_map<std::string, const Term *> m_definitions;
    std::unordered_map<const Term *, size_t> m_temp_counts;
    size_t m_temp_depth;
};

Corpus::Linker::Linker (Dag & dag)
    : m_dag(dag),
      m_definitions(),
      m_temp_counts(),
      m_temp_depth(0)
{
    const Term * hole = m_dag.hole();
    for (const Term * term : m_dag.variables()) {
        m_definitions.insert(std::make_pair(term->name, hole));
        m_temp_counts.insert(std::make_pair(term, 0));
    }
}

inline void Corpus::Linker::define (
        const std::string & name,
        const Term * term)
{
    m_definitions[name] = term;
}

inline const Corpus::Term * Corpus::Linker::link (
        const Term * term,
        size_t depth)
{
    m_temp_depth = depth;
    return link(term);
}

const Corpus::Term * Corpus::Linker::link (const Term * term)
{
    switch (term->arity) {
        case Term::OB:
        case Term::HOLE:
        case Term::NULLARY_FUNCTION:
            return term;

        case Term::INJECTIVE_FUNCTION:
            return m_dag.injective_function(term->name, link(term->arg0));

        case Term::BINARY_FUNCTION:
            return m_dag.binary_function(
                term->name,
                link(term->arg0),
                link(term->arg1));

        case Term::SYMMETRIC_FUNCTION:
            return m_dag.symmetric_function(
                term->name,
                link(term->arg0),
                link(term->arg1));

        case Term::BINARY_RELATION:
            return m_dag.binary_relation(
                term->name,
                link(term->arg0),
                link(term->arg1));

        case Term::VARIABLE:
            size_t & count = m_temp_counts[term];
            if (count == m_temp_depth) {
                return m_dag.hole();
            } else {
                ++count;
                const Term * result = link(m_definitions[term->name]);
                --count;
                return result;
            }
    }

    return nullptr; // never reached
}

//----------------------------------------------------------------------------
// Corpus

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
    Linker linker(m_dag);
    for (const auto & line : lines) {
        if (line.is_definition()) {
            const std::string & name = line.maybe_name;
            const Term * term = m_parser.parse(line.code);
            linker.define(name, term);
        }
    }

    // then do a maximally-linked pass
    Diff diff;
    for (const auto & line : lines) {
        const Term * term = m_parser.parse(line.code);
        diff.lines.push_back(term);
    }

    TODO("compute removed, added");

    if (not error_log.empty()) {
        POMAGMA_WARN("found " << error_log.size() << " errors");
    }
    return diff;
}

} // namespace pomagma
