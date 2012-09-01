#ifndef POMAGMA_NULLARY_FUNCTION_HPP
#define POMAGMA_NULLARY_FUNCTION_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include "carrier.hpp"

namespace pomagma
{

class NullaryFunction : noncopyable
{
    const Carrier & m_carrier;
    const DenseSet m_support; // aliased
    mutable std::atomic<Ob> m_value;

    mutable AssertSharedMutex m_mutex;
    typedef AssertSharedMutex::SharedLock SharedLock;
    typedef AssertSharedMutex::UniqueLock UniqueLock;

public:

    NullaryFunction (const Carrier & carrier);
    void move_from (const NullaryFunction & other);
    void validate () const;

    // safe operations
    bool defined () const;
    Ob find () const;
    void insert (Ob val) const;

    // unsafe operations
    void remove (Ob ob);
    void merge (Ob dep, Ob rep);

private:

    const DenseSet & support () const { return m_support; }
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

    Ob old_val = 0;
    while (not m_value.compare_exchange_weak(old_val, val)) {
        val = m_carrier.ensure_equal(old_val, val);
        if (val == old_val) break;
    }
}

} // namespace pomagma

#endif // POMAGMA_NULLARY_FUNCTION_HPP
