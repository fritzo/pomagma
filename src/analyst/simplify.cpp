#include <pomagma/analyst/simplify.hpp>
#include <pomagma/atlas/parser.hpp>

namespace pomagma {

class Simplifier::Reducer {
   public:
    Reducer(Signature& signature, const std::vector<std::string>& routes)
        : m_signature(signature),
          m_nless(*signature.binary_relation("NLESS")),
          m_routes(routes) {
        POMAGMA_ASSERT(signature.binary_relation("NLESS") != nullptr,
                       "NLESS is not defined");
    }

    struct Term {
        Ob ob;
        std::string route;
    };

    Term reduce(const std::string& token, const NullaryFunction* fun) {
        Term val;
        val.ob = fun->find();
        val.route = val.ob ? m_routes[val.ob] : token;
        return val;
    }

    Term reduce(const std::string& token, const InjectiveFunction* fun,
                const Term& key) {
        Term val;
        val.ob = key.ob ? fun->find(key.ob) : 0;
        val.route = val.ob ? m_routes[val.ob] : token + " " + key.route;
        return val;
    }

    Term reduce(const std::string& token, const BinaryFunction* fun,
                const Term& lhs, const Term& rhs) {
        Term val;
        val.ob = lhs.ob and rhs.ob ? fun->find(lhs.ob, rhs.ob) : 0;
        val.route = val.ob ? m_routes[val.ob]
                           : token + " " + lhs.route + " " + rhs.route;
        return val;
    }

    Term reduce(const std::string& token, const SymmetricFunction* fun,
                const Term& lhs, const Term& rhs) {
        Term val;
        val.ob = lhs.ob and rhs.ob ? fun->find(lhs.ob, rhs.ob) : 0;
        val.route = val.ob ? m_routes[val.ob]
                           : token + " " + lhs.route + " " + rhs.route;
        return val;
    }

    Term reduce(const std::string& token, const UnaryRelation* rel,
                const Term& key) {
        if (key.ob) {
            if (rel->find(key.ob)) {
                return semi_true();
            }
            std::string negated = m_signature.negate(token);
            if (auto* negated_rel = m_signature.unary_relation(negated)) {
                if (negated_rel->find(key.ob)) {
                    return semi_false();
                }
            }
        }
        return {0, token + " " + key.route};
    }

    Term reduce(const std::string& token, const BinaryRelation* rel,
                const Term& lhs, const Term& rhs) {
        if (lhs.ob and rhs.ob) {
            if (rel->find(lhs.ob, rhs.ob)) {
                return semi_true();
            }
            std::string negated = m_signature.negate(token);
            if (auto* negated_rel = m_signature.binary_relation(negated)) {
                if (negated_rel->find(lhs.ob, rhs.ob)) {
                    return semi_false();
                }
            }
        }
        return {0, token + " " + lhs.route + " " + rhs.route};
    }

    Term reduce_equal(const Term& lhs, const Term& rhs) {
        if (lhs.ob and rhs.ob) {
            if (lhs.ob == rhs.ob) {
                return semi_true();
            }
            if (m_nless.find(lhs.ob, rhs.ob) or m_nless.find(rhs.ob, lhs.ob)) {
                return semi_false();
            }
        }
        if (lhs.route == rhs.route) {
            return semi_true();
        }
        return {0, "EQUAL " + lhs.route + " " + rhs.route};
    }

    Term reduce_hole() { return {0, "HOLE"}; }

    Term reduce_var(const std::string& name) { return {0, "VAR " + name}; }

    Term reduce_error(const std::string& token) { return {0, token}; }

   private:
    Term semi_true() { return {0, "I"}; }
    Term semi_false() { return {0, "BOT"}; }

    Signature& m_signature;
    const BinaryRelation& m_nless;
    const std::vector<std::string>& m_routes;
};

class Simplifier::Parser : public ExprParser<Simplifier::Reducer> {
   public:
    Parser(Signature& signature, const std::vector<std::string>& routes,
           std::vector<std::string>& error_log)
        : ExprParser<Simplifier::Reducer>(signature, m_reducer, error_log),
          m_reducer(signature, routes) {}

   private:
    Simplifier::Reducer m_reducer;
};

Simplifier::Simplifier(Signature& signature,
                       const std::vector<std::string>& routes,
                       std::vector<std::string>& error_log)
    : m_parser(*new Parser(signature, routes, error_log)) {}

Simplifier::~Simplifier() { delete &m_parser; }

std::string Simplifier::simplify(const std::string& expression) {
    return m_parser.parse(expression).route;
}

}  // namespace pomagma
