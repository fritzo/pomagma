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
    const DenseSet m_support; // aliased
    mutable DenseSet m_set;
    mutable DenseSet m_inverse_set;
    std::atomic<Ob> * const m_values;
    std::atomic<Ob> * const m_inverse;

    mutable AssertSharedMutex m_mutex;
    typedef AssertSharedMutex::SharedLock SharedLock;
    typedef AssertSharedMutex::UniqueLock UniqueLock;

public:

    InjectiveFunction (const Carrier & carrier);
    ~InjectiveFunction ();
    void move_from (const InjectiveFunction & other); // for growing
    void validate () const;

    // safe operations
    const DenseSet & defined () const { return m_set; }
    const DenseSet & inverse_defined () const { return m_inverse_set; }
    bool defined (Ob key) const;
    bool inverse_defined (Ob key) const;
    Ob find (Ob key) const { return value(key); }
    Ob inverse_find (Ob val) const { return inverse(val); }
    void insert (Ob key, Ob val) const;

    // unsafe operations
    void remove (Ob ob);
    void merge (Ob dep, Ob rep);

private:

    size_t item_dim () const { return m_support.item_dim(); }
    const DenseSet & support () const { return m_support; }
    std::atomic<Ob> & value (Ob key);
    std::atomic<Ob> & inverse (Ob val);
    Ob value (Ob key) const;
    Ob inverse (Ob val) const;
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

inline std::atomic<Ob> & InjectiveFunction::value (Ob key)
{
    POMAGMA_ASSERT_RANGE_(5, key, item_dim());
    return m_values[key];
}

inline Ob InjectiveFunction::value (Ob key) const
{
    POMAGMA_ASSERT_RANGE_(5, key, item_dim());
    return m_values[key];
}

inline std::atomic<Ob> & InjectiveFunction::inverse (Ob val)
{
    POMAGMA_ASSERT_RANGE_(5, val, item_dim());
    return m_inverse[val];
}

inline Ob InjectiveFunction::inverse (Ob val) const
{
    POMAGMA_ASSERT_RANGE_(5, val, item_dim());
    return m_inverse[val];
}

} // namespace pomagma

#endif // POMAGMA_INJECTIVE_FUNCTION_HPP
