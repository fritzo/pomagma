#include "parser.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include <pomagma/util/parser_impl.hpp>

namespace pomagma
{

inline Ob Parser::Policy::check_insert (Ob val)
{
    if (val) {
        bool_ref contained = m_set(val);
        if (unlikely(not contained.load())) {
            POMAGMA_ASSERT_LT(m_size, m_capacity);
            contained.one();
            m_size += 1;
        }
    }
    return val;
}

inline Ob Parser::Policy::check_insert (
        const NullaryFunction * fun)
{
    return check_insert(fun->find());
}

inline Ob Parser::Policy::check_insert (
        const InjectiveFunction * fun,
        Ob key)
{
    return check_insert(fun->find(key));
}

inline Ob Parser::Policy::check_insert (
        const BinaryFunction * fun,
        Ob lhs,
        Ob rhs)
{
    return check_insert(fun->find(lhs, rhs));
}

inline Ob Parser::Policy::check_insert (
        const SymmetricFunction * fun,
        Ob lhs,
        Ob rhs)
{
    return check_insert(fun->find(lhs, rhs));
}

} // namespace pomagma
