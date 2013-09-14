#pragma once

#include "util.hpp"
#include "carrier.hpp"
#include <pomagma/platform/sequential/dense_set.hpp>

namespace pomagma
{

class NullaryFunction : noncopyable
{
    const Carrier & m_carrier;
    mutable Ob m_value;

public:

    NullaryFunction (const Carrier & carrier);
    NullaryFunction (const Carrier & carrier, NullaryFunction && other);
    void validate () const;
    void log_stats (const std::string & prefix) const;

    // raw operations
    void raw_insert (Ob val);
    void update () {}
    void clear () { m_value = 0; }

    // safe operations
    bool defined () const { return m_value; }
    Ob find () const { return m_value; }
    void insert (Ob val) const;
    void update_values () const {} // postcondition: all values are reps

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

inline void NullaryFunction::insert (Ob val) const
{
    POMAGMA_ASSERT5(val, "tried to set value to zero");
    POMAGMA_ASSERT5(support().contains(val), "unsupported value: " << val);

    m_carrier.set_or_merge(m_value, val);
}

} // namespace pomagma
