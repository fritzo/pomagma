#pragma once

#include "util.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include <pomagma/util/parser.hpp>

namespace pomagma
{

class Parser::Policy : noncopyable
{
    DenseSet & m_set;
    size_t m_size;
    const size_t m_capacity;

public:

    Policy (DenseSet & s, size_t capacity)
        : m_set(s),
          m_size(s.count_items()),
          m_capacity(capacity)
    {
        POMAGMA_ASSERT_LE(m_size, m_capacity);
    }

    Ob check_insert (const NullaryFunction * fun)
    {
        return check_insert(fun->find());
    }

    Ob check_insert (const InjectiveFunction * fun, Ob key)
    {
        return check_insert(fun->find(key));
    }

    Ob check_insert (const BinaryFunction * fun, Ob lhs, Ob rhs)
    {
        return check_insert(fun->find(lhs, rhs));
    }

    Ob check_insert (const SymmetricFunction * fun, Ob lhs, Ob rhs)
    {
        return check_insert(fun->find(lhs, rhs));
    }

private:

    Ob check_insert (Ob val)
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
};

} // namespace pomagma
