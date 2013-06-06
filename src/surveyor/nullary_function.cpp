#include "nullary_function.hpp"
#include <pomagma/platform/aligned_alloc.hpp>
#include <cstring>

namespace pomagma
{

static void noop_callback (const NullaryFunction *) {}

NullaryFunction::NullaryFunction (
        const Carrier & carrier,
        void (*insert_callback) (const NullaryFunction *))
    : m_carrier(carrier),
      m_value(0),
      m_insert_callback(insert_callback ? insert_callback : noop_callback)
{
    POMAGMA_DEBUG("creating NullaryFunction");
}

void NullaryFunction::validate () const
{
    SharedLock lock(m_mutex);

    POMAGMA_INFO("Validating NullaryFunction");

    Ob value = m_value;
    if (value) {
        POMAGMA_ASSERT(support().contains(value),
                "unsupported value: " << value);
    }
}

void NullaryFunction::log_stats () const
{
    POMAGMA_INFO((m_value.load() ? "defined" : "undefined"));
}

void NullaryFunction::unsafe_merge (Ob dep)
{
    UniqueLock lock(m_mutex);

    Ob rep = m_carrier.find(dep);
    POMAGMA_ASSERT4(rep < dep, "bad merge: " << dep << "," << rep);
    POMAGMA_ASSERT_RANGE_(4, dep, support().item_dim());
    POMAGMA_ASSERT_RANGE_(4, rep, support().item_dim());

    if (m_value == dep) {
        m_value = rep;
    }
}

} // namespace pomagma
