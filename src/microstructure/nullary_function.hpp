#pragma once

#include "util.hpp"
#include <pomagma/platform/concurrent/dense_set.hpp>
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
    void validate () const;
    void log_stats (const std::string & prefix) const;

    // raw operations
    void raw_insert (Ob val);
    void update () {}
    void clear () { m_value.store(0); }

    // relaxed operations
    bool defined () const;
    Ob find () const;
    void insert (Ob val) const;

    // strict operations
    void unsafe_merge (Ob dep);

private:

    const DenseSet & support () const { return m_carrier.support(); }
};

inline bool NullaryFunction::defined () const
{
    SharedLock lock(m_mutex);
    return m_value.load(relaxed);
}

inline Ob NullaryFunction::find () const
{
    SharedLock lock(m_mutex);
    return m_value.load(acquire);
}

inline void NullaryFunction::raw_insert (Ob val)
{
    POMAGMA_ASSERT5(val, "tried to set value to zero");
    POMAGMA_ASSERT5(support().contains(val), "unsupported value: " << val);

    m_value.store(val, relaxed);
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
