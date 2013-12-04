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
            std::string negated;
            if (name == "LESS") negated = "NLESS"; // HACK
            if (name == "NLESS") negated = "LESS"; // HACK
            if (auto * rel = m_signature.binary_relation(negated)) {
                if (rel->find(lhs->ob, rhs->ob)) {
                    return falsey();
                }
            }
        }
        return get(Term(Term::BINARY_RELATION, name, lhs, rhs));
    }
    const Term * variable (
            const std::string & name)
    {
        return get(Term(Term::VARIABLE, name));
    }

    typedef std::unordered_set<Term, Term::Hash, Term::Equal> Terms;
    const Terms & terms () const { return m_terms; }

private:

    const Term * get (Term && key) { return & * m_terms.insert(key).first; }

    Signature & m_signature;
    Terms m_terms;
};


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
    Diff diff;
    m_definitions.clear();
    for (const auto & line : lines) {
        const Term * term = m_parser.parse(line.code);
        diff.lines.push_back(term);
        const std::string & name = line.maybe_name;
        if (not name.empty()) {
            auto pair = m_definitions.insert(std::make_pair(name, term));
            if (not pair.second) {
                std::string message = "duplicate definition: " + name;
                POMAGMA_WARN(message);
                error_log.push_back(message);
            }
        }
    }
    for (const Term & term : m_dag.terms()) {
        if (term.arity == Term::VARIABLE) {
            const std::string & name = term.name;
            if (m_definitions.find(name) == m_definitions.end()) {
                std::string message = "missing definition: " + name;
                POMAGMA_WARN(message);
                error_log.push_back(message);
            }
        }
    }
    TODO("compute removed, added");
    return diff;
}

} // namespace pomagma
