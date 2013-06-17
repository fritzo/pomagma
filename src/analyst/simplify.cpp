#include "simplify.hpp"
#include <pomagma/macrostructure/structure_impl.hpp>
#include <pomagma/platform/parser.hpp>
#include <tuple>

namespace pomagma
{

class SimplifyReducer
{
public:

    typedef ParsedTerm Term;

    SimplifyReducer (const std::vector<std::string> & routes)
        : m_routes(routes)
    {
    }

private:

    const std::vector<std::string> & m_routes;
};

class Simplifier : noncopyable
{
public:

    Simplifier (
            const Signature & signature,
            const std::vector<std::string> & routes)
        : m_signature(signature),
          m_routes(routes)
    {
    }

    ParsedTerm simplify (const std::string & term)
    {
        m_stream.str(term);
        ParsedTerm parsed_term = pop_simplify();
        POMAGMA_ASSERT(m_stream.eof(), "unexpected tokens in " << m_stream);
        return parsed_term;
    }

private:

    ParsedTerm pop_simplify ();

    const Signature & m_signature;
    const std::vector<std::string> & m_routes;
    std::istringstream m_stream;
};

ParsedTerm Simplifier::pop_simplify ()
{
    std::string token;
    POMAGMA_ASSERT(std::getline(m_stream, token, ' '),
            "expression terminated prematurely");

    ParsedTerm val;
    if (const auto * fun = m_signature.nullary_functions(token)) {
        val.ob = fun->find();
        val.route = val.ob ? m_routes[val.ob] : token;
    } else if (const auto * fun = m_signature.injective_functions(token)) {
        ParsedTerm key = pop_simplify();
        val.ob = key.ob ? fun->find(key.ob) : 0;
        val.route = val.ob ? m_routes[val.ob] : token + " " + key.route;
    } else if (const auto * fun = m_signature.binary_functions(token)) {
        ParsedTerm lhs = pop_simplify();
        ParsedTerm rhs = pop_simplify();
        val.ob = lhs.ob and rhs.ob ? fun->find(lhs.ob, rhs.ob) : 0;
        val.route = val.ob
                  ? m_routes[val.ob]
                  : token + " " + lhs.route + " " + rhs.route;
    } else if (const auto * fun = m_signature.symmetric_functions(token)) {
        ParsedTerm lhs = pop_simplify();
        ParsedTerm rhs = pop_simplify();
        val.ob = lhs.ob and rhs.ob ? fun->find(lhs.ob, rhs.ob) : 0;
        val.route = val.ob
                  ? m_routes[val.ob]
                  : token + " " + lhs.route + " " + rhs.route;
    } else {
        POMAGMA_ERROR("unrecognized token: " << token);
    }

    return val;
}

ParsedTerm simplify (
        Structure & structure,
        const std::vector<std::string> & routes,
        const std::string term)
{
    POMAGMA_DEBUG("Simplifying " << term);

    Simplifier simplifier(structure.signature(), routes);
    ParsedTerm parsed_term = simplifier.simplify(term);
    return parsed_term;
}

void batch_simplify(
        Structure & structure,
        const std::vector<std::string> & routes,
        const char * source_file,
        const char * destin_file)
{
    POMAGMA_INFO("simplifying expressions");
    pomagma::Simplifier simplifier(structure.signature(), routes);

    std::ofstream destin(destin_file);
    POMAGMA_ASSERT(destin, "failed to open " << destin_file);
    destin << "# expressions simplifed by pomagma\n";

    for (LineParser iter(source_file); iter.ok(); iter.next()) {
        const std::string & expression = * iter;
        POMAGMA_DEBUG("simplifying " << expression);
        ParsedTerm simplified = simplifier.simplify(expression);
        POMAGMA_DEBUG("simplified to " << simplified.route);
        destin << simplified.route << "\n";
    }
}

} // namespace pomagma
