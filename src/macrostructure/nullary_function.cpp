#include "nullary_function.hpp"
#include <pomagma/platform/aligned_alloc.hpp>
#include <cstring>

namespace pomagma
{

NullaryFunction::NullaryFunction (const Carrier & carrier)
    : m_carrier(carrier),
      m_value(0)
{
    POMAGMA_DEBUG("creating NullaryFunction");
}

NullaryFunction::NullaryFunction (
        const Carrier & carrier,
        NullaryFunction && other)
    : m_carrier(carrier),
      m_value(other.m_value)
{
    POMAGMA_DEBUG("resizing NullaryFunction");
    POMAGMA_ASSERT(
        m_value <= m_carrier.item_dim(),
        "value not supported by carrier");
}

void NullaryFunction::validate () const
{
    POMAGMA_INFO("Validating NullaryFunction");

    Ob value = m_value;
    if (value) {
        POMAGMA_ASSERT(support().contains(value),
                "unsupported value: " << value);
    }
}

void NullaryFunction::log_stats (const std::string & prefix) const
{
    POMAGMA_INFO(prefix << " " << (m_value ? "defined" : "undefined"));
}

void NullaryFunction::unsafe_merge (Ob dep)
{
    Ob rep = m_carrier.find(dep);
    POMAGMA_ASSERT4(rep < dep, "bad merge: " << dep << "," << rep);
    POMAGMA_ASSERT_RANGE_(4, dep, support().item_dim());
    POMAGMA_ASSERT_RANGE_(4, rep, support().item_dim());

    if (m_value == dep) {
        m_value = rep;
    }
}

} // namespace pomagma
