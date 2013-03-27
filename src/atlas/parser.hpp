#pragma once

#include "util.hpp"
#include <pomagma/util/parser.hpp>
#include <pomagma/util/sequential_dense_set.hpp>

namespace pomagma
{

class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;

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

    size_t size () { return m_size; }

    Ob check_insert (const NullaryFunction * fun);
    Ob check_insert (const InjectiveFunction * fun, Ob key);
    Ob check_insert (const BinaryFunction * fun, Ob lhs, Ob rhs);
    Ob check_insert (const SymmetricFunction * fun, Ob lhs, Ob rhs);

private:

    Ob check_insert (Ob val);
};

} // namespace pomagma
