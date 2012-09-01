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

void NullaryFunction::move_from (const NullaryFunction & other)
{
    POMAGMA_DEBUG("Copying NullaryFunction");

    m_value = other.m_value.load();
}

void NullaryFunction::validate () const
{
    SharedLock lock(m_mutex);

    POMAGMA_DEBUG("Validating NullaryFunction");

    Ob value = m_value;
    if (value) {
        POMAGMA_ASSERT(m_support.contains(value),
                "unsupported value: " << value);
    }
}

void NullaryFunction::remove (Ob ob)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT_RANGE_(4, ob, m_support.item_dim());

    if (m_value == ob) {
        m_value = 0;
    }
}

void NullaryFunction::merge (Ob dep, Ob rep)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT4(rep < dep, "bad merge: " << dep << "," << rep);
    POMAGMA_ASSERT_RANGE_(4, dep, m_support.item_dim());
    POMAGMA_ASSERT_RANGE_(4, rep, m_support.item_dim());

    if (m_value == dep) {
        m_value = rep;
    }
}

} // namespace pomagma
