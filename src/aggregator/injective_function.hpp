#pragma once

#include "util.hpp"
#include "carrier.hpp"
#include <pomagma/util/sequential_dense_set.hpp>

namespace pomagma
{

class InjectiveFunction : noncopyable
{
    Carrier & m_carrier;
    DenseSet m_set;
    DenseSet m_inverse_set;
    Ob * const m_values;
    Ob * const m_inverse;

public:

    InjectiveFunction (Carrier & carrier);
    ~InjectiveFunction ();
    void validate () const;
    void log_stats () const;

    // raw operations
    size_t count_items () const { return m_set.count_items(); }
    Ob raw_find (Ob key) const;
    void raw_insert (Ob key, Ob val);
    void clear ();

    // relaxed operations
    // m_values & m_inverse are source of truth; m_set & m_inverse_set lag
    const DenseSet & defined () const { return m_set; }
    const DenseSet & inverse_defined () const { return m_inverse_set; }
    bool defined (Ob key) const;
    bool inverse_defined (Ob key) const;
    Ob find (Ob key) const;
    Ob inverse_find (Ob val) const;
    DenseSet::Iterator iter () const { return m_set.iter(); }
    DenseSet::Iterator inverse_iter () const { return m_inverse_set.iter(); }
    void insert (Ob key, Ob val);

    // strict operations
    void unsafe_merge (Ob dep);

private:

    const DenseSet & support () const { return m_carrier.support(); }
    size_t item_dim () const { return support().item_dim(); }
};

inline bool InjectiveFunction::defined (Ob key) const
{
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    return m_set.contains(key);
}

inline bool InjectiveFunction::inverse_defined (Ob key) const
{
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    return m_inverse_set.contains(key);
}

inline Ob InjectiveFunction::raw_find (Ob key) const
{
    POMAGMA_ASSERT_RANGE_(5, key, item_dim());
    return m_values[key];
}

inline Ob InjectiveFunction::find (Ob key) const
{
    POMAGMA_ASSERT_RANGE_(5, key, item_dim());
    return m_values[key];
}

inline Ob InjectiveFunction::inverse_find (Ob val) const
{
    POMAGMA_ASSERT_RANGE_(5, val, item_dim());
    return m_inverse[val];
}

inline void InjectiveFunction::raw_insert (Ob key, Ob val)
{
    POMAGMA_ASSERT5(val, "tried to set val to zero at " << key);
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    m_values[key] = val;
    m_set(key).one();

    m_inverse[val] = key;
    m_inverse_set(val).one();
}

inline void InjectiveFunction::insert (Ob key, Ob val)
{
    POMAGMA_ASSERT5(val, "tried to set val to zero at " << key);
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    if (m_carrier.set_or_merge(m_values[key], val)) {
        m_set(key).one();
    }

    if (m_carrier.set_or_merge(m_inverse[val], key)) {
        m_inverse_set(val).one();
    }
}

} // namespace pomagma
