#pragma once

#include "util.hpp"
#include "carrier.hpp"
#include <pomagma/util/sequential_dense_set.hpp>

namespace pomagma
{

class NullaryFunction : noncopyable
{
    Carrier & m_carrier;
    Ob m_value;

public:

    NullaryFunction (Carrier & carrier);
    void validate () const;
    void log_stats () const;

    // raw operations
    void clear () { m_value = 0; }
    void raw_insert (Ob val);

    // safe operations
    bool defined () const { return m_value; }
    Ob find () const { return m_value; }
    void insert (Ob val);

    // unsafe operations
    void unsafe_merge (Ob dep);

private:

    const DenseSet & support () const { return m_carrier.support(); }
};

inline void NullaryFunction::raw_insert (Ob val)
{
    POMAGMA_ASSERT5(val, "tried to set value to zero");
    POMAGMA_ASSERT5(support().contains(val), "unsupported value: " << val);

    m_value = val;
}

inline void NullaryFunction::insert (Ob val)
{
    POMAGMA_ASSERT5(val, "tried to set value to zero");
    POMAGMA_ASSERT5(support().contains(val), "unsupported value: " << val);

    if (m_value) {
        m_carrier.ensure_equal(m_value, val);
    } else {
        m_value = val;
    }
}

} // namespace pomagma
