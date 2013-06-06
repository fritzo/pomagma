#pragma once

#include "util.hpp"
#include <pomagma/platform/sampler.hpp>
#include <pomagma/platform/sequential_dense_set.hpp>

namespace pomagma
{

class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;

class Sampler::Policy : noncopyable
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

    bool ok () const { return m_size < m_capacity; }
    size_t size () const { return m_size; }

    Ob sample (const NullaryFunction & fun);
    Ob sample (const InjectiveFunction & fun, Ob key);
    Ob sample (const BinaryFunction & fun, Ob lhs, Ob rhs);
    Ob sample (const SymmetricFunction & fun, Ob lhs, Ob rhs);

private:

    Ob sample (Ob val);
};

} // namespace pomagma
