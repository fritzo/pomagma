#include "parser.hpp"
#include "carrier.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include <pomagma/platform/parser_impl.hpp>

namespace pomagma
{

inline Ob Parser::Policy::check_insert (
        const NullaryFunction * fun) const
{
    Ob val = fun->find();
    if (not val) {
        val = carrier.try_insert();
        POMAGMA_ASSERT(val, "carrier is full");
        fun->insert(val);
    }
    return val;
}

inline Ob Parser::Policy::check_insert (
        const InjectiveFunction * fun,
        Ob key) const
{
    Ob val = fun->find(key);
    if (not val) {
        val = carrier.try_insert();
        POMAGMA_ASSERT(val, "carrier is full");
        fun->insert(key, val);
    }
    return val;
}

inline Ob Parser::Policy::check_insert (
        const BinaryFunction * fun,
        Ob lhs,
        Ob rhs) const
{
    Ob val = fun->find(lhs, rhs);
    if (not val) {
        val = carrier.try_insert();
        POMAGMA_ASSERT(val, "carrier is full");
        fun->insert(lhs, rhs, val);
    }
    return val;
}

inline Ob Parser::Policy::check_insert (
        const SymmetricFunction * fun,
        Ob lhs,
        Ob rhs) const
{
    Ob val = fun->find(lhs, rhs);
    if (not val) {
        val = carrier.try_insert();
        POMAGMA_ASSERT(val, "carrier is full");
        fun->insert(lhs, rhs, val);
    }
    return val;
}

} // namespace pomagma
