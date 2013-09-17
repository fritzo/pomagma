#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure_impl.hpp>
#include <pomagma/platform/parser.hpp>

namespace pomagma
{

struct SimplifyTerm
{
    Ob ob;
    std::string route;
};

class SimplifyReducer : noncopyable
{
public:

    typedef SimplifyTerm Term;

    SimplifyReducer (const std::vector<std::string> & routes)
        : m_routes(routes)
    {
    }

    SimplifyTerm reduce (
            const std::string & token,
            const NullaryFunction * fun)
    {
        SimplifyTerm val;
        val.ob = fun->find();
        val.route = val.ob ? m_routes[val.ob] : token;
        return val;
    }

    SimplifyTerm reduce (
            const std::string & token,
            const InjectiveFunction * fun,
            SimplifyTerm key)
    {
        SimplifyTerm val;
        val.ob = key.ob ? fun->find(key.ob) : 0;
        val.route = val.ob ? m_routes[val.ob] : token + " " + key.route;
        return val;
    }

    SimplifyTerm reduce (
            const std::string & token,
            const BinaryFunction * fun,
            SimplifyTerm lhs,
            SimplifyTerm rhs)
    {
        SimplifyTerm val;
        val.ob = lhs.ob and rhs.ob ? fun->find(lhs.ob, rhs.ob) : 0;
        val.route = val.ob
                  ? m_routes[val.ob]
                  : token + " " + lhs.route + " " + rhs.route;
        return val;
    }

    SimplifyTerm reduce (
            const std::string & token,
            const SymmetricFunction * fun,
            SimplifyTerm lhs,
            SimplifyTerm rhs)
    {
        SimplifyTerm val;
        val.ob = lhs.ob and rhs.ob ? fun->find(lhs.ob, rhs.ob) : 0;
        val.route = val.ob
                  ? m_routes[val.ob]
                  : token + " " + lhs.route + " " + rhs.route;
        return val;
    }

private:

    const std::vector<std::string> & m_routes;
};

class SimplifyParser : public Parser<SimplifyReducer>
{
public:

    SimplifyParser (
            Signature & signature,
            const std::vector<std::string> & routes)
        : Parser<SimplifyReducer>(signature, m_reducer),
          m_reducer(routes)
    {
    }

    std::string simplify (const std::string & expression);

private:

    SimplifyReducer m_reducer;
};

size_t batch_simplify(
        Structure & structure,
        const std::vector<std::string> & routes,
        const char * source_file,
        const char * destin_file);


} // namespace pomagma
