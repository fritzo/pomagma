#ifndef POMAGMA_INJECTIVE_FUNCTION_HPP
#define POMAGMA_INJECTIVE_FUNCTION_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include "carrier.hpp"

namespace pomagma
{

class InjectiveFunction : noncopyable
{
    const Carrier & m_carrier;
    mutable DenseSet m_set;
    mutable DenseSet m_inverse_set;
    std::atomic<Ob> * const m_values;
    std::atomic<Ob> * const m_inverse;
    void (*m_insert_callback) (Ob);

    mutable AssertSharedMutex m_mutex;
    typedef AssertSharedMutex::SharedLock SharedLock;
    typedef AssertSharedMutex::UniqueLock UniqueLock;

public:

    InjectiveFunction (
        const Carrier & carrier,
        void (*insert_callback) (Ob) = nullptr);
    ~InjectiveFunction ();
    void copy_from (const InjectiveFunction & other); // for growing
    void validate () const;

    // relaxed operations
    const DenseSet & defined () const { return m_set; }
    const DenseSet & inverse_defined () const { return m_inverse_set; }
    bool defined (Ob key) const;
    bool inverse_defined (Ob key) const;
    Ob find (Ob key) const;
    Ob inverse_find (Ob val) const;
    DenseSet::Iterator iter () const { return m_set.iter(); }
    DenseSet::Iterator inverse_iter () const { return m_inverse_set.iter(); }
    void insert (Ob key, Ob val) const;

    // strict operations
    void unsafe_remove (Ob ob);
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

inline void InjectiveFunction::insert (Ob key, Ob val) const
{
    SharedLock lock(m_mutex);

    POMAGMA_ASSERT5(val, "tried to set val to zero at " << key);
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    if (m_carrier.set_and_merge(m_values[key], val)) {
        m_set(key).one();
        m_insert_callback(key);
    }

    if (m_carrier.set_and_merge(m_inverse[val], key)) {
        m_inverse_set(val).one();
    }
}

} // namespace pomagma

#endif // POMAGMA_INJECTIVE_FUNCTION_HPP
