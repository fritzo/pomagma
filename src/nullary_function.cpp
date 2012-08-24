#include "nullary_function.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

NullaryFunction::NullaryFunction (const Carrier & carrier)
    : m_carrier(carrier),
      m_support(carrier.support(), yes_copy_construct),
      m_value(0)
{
    POMAGMA_DEBUG("creating NullaryFunction");
}

// for growing
void NullaryFunction::move_from (const NullaryFunction & other)
{
    POMAGMA_DEBUG("Copying NullaryFunction");

    m_value = other.m_value;
}

//----------------------------------------------------------------------------
// Diagnostics

void NullaryFunction::validate () const
{
    POMAGMA_DEBUG("Validating NullaryFunction");

    if (m_value) {
        POMAGMA_ASSERT(m_support.contains(m_value),
                "unsupported value: " << m_value);
    }
}

//----------------------------------------------------------------------------
// Operations

void NullaryFunction::remove(const oid_t dep)
{
    POMAGMA_ASSERT_RANGE_(4, dep, m_support.item_dim());

    if (m_value == dep) {
        m_value = 0;
    }
}

void NullaryFunction::merge(const oid_t dep, const oid_t rep)
{
    POMAGMA_ASSERT4(rep != dep, "self merge: " << dep << "," << rep);
    POMAGMA_ASSERT_RANGE_(4, dep, m_support.item_dim());
    POMAGMA_ASSERT_RANGE_(4, rep, m_support.item_dim());

    if (m_value == dep) {
        m_value = rep;
    }
}

} // namespace pomagma
