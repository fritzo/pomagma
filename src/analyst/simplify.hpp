#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure_impl.hpp>

namespace pomagma
{

class Simplifier
{
public:

    Simplifier (
            Signature & signature,
            const std::vector<std::string> & routes,
            std::vector<std::string> & error_log);

    std::string simplify (const std::string & expression);

private:

    struct Term
    {
        Ob ob;
        std::string route;
    };

    void begin (const std::string & expression);
    std::string parse_token ();
    Term parse_term ();
    void end ();

    Term reduce (
            const std::string & token,
            const NullaryFunction * fun);
    Term reduce (
            const std::string & token,
            const InjectiveFunction * fun,
            const Term & key);
    Term reduce (
            const std::string & token,
            const BinaryFunction * fun,
            const Term & lhs,
            const Term & rhs);
    Term reduce (
            const std::string & token,
            const SymmetricFunction * fun,
            const Term & lhs,
            const Term & rhs);
    Term reduce (
            const std::string & token,
            const UnaryRelation * rel,
            const Term & key);
    Term reduce (
            const std::string & token,
            const BinaryRelation * rel,
            const Term & lhs,
            const Term & rhs);
    Term reduce_equal (const Term & lhs, const Term & rhs);

    Term semi_true () { return {0, "I"}; }
    Term semi_false () { return {0, "BOT"}; }

    Signature & m_signature;
    const BinaryRelation & m_nless;
    const std::vector<std::string> & m_routes;
    std::vector<std::string> & m_error_log;
    std::istringstream m_stream;
};

} // namespace pomagma
