#pragma once

#include "util.hpp"
#include "dense_set.hpp"
#include "carrier.hpp"

namespace pomagma
{

class NullaryFunction : noncopyable
{
    const Carrier & m_carrier;
    mutable std::atomic<Ob> m_value;

    mutable AssertSharedMutex m_mutex;
    typedef AssertSharedMutex::SharedLock SharedLock;
    typedef AssertSharedMutex::UniqueLock UniqueLock;
    void (*m_insert_callback) (const NullaryFunction *);

public:

    NullaryFunction (
        const Carrier & carrier,
        void (*insert_callback) (const NullaryFunction *) = nullptr);
    void copy_from (const NullaryFunction & other);
    void validate () const;

    // relaxed operations
    bool defined () const;
    Ob find () const;
    void insert (Ob val) const;

    // strict operations
    void unsafe_remove (Ob ob);
    void unsafe_merge (Ob dep);

private:

    const DenseSet & support () const { return m_carrier.support(); }
};

inline bool NullaryFunction::defined () const
{
    SharedLock lock(m_mutex);
    return m_value;
}

inline Ob NullaryFunction::find () const
{
    SharedLock lock(m_mutex);
    return m_value;
}

inline void NullaryFunction::insert (Ob val) const
{
    SharedLock lock(m_mutex);

    POMAGMA_ASSERT5(val, "tried to set value to zero");
    POMAGMA_ASSERT5(support().contains(val), "unsupported value: " << val);

    if (m_carrier.set_and_merge(m_value, val)) {
        m_insert_callback(this);
    }
}

} // namespace pomagma
