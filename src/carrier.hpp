#ifndef POMAGMA_CARRIER_HPP
#define POMAGMA_CARRIER_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include "threading.hpp"
#include <functional>
#include <algorithm>
#include <vector>
#include <atomic>

namespace pomagma
{

class Carrier : noncopyable
{
    DenseSet m_support;
    std::atomic<size_t> m_item_count;
    mutable std::atomic<size_t> m_rep_count;
    typedef std::atomic<Ob> Rep;
    Rep * const m_reps;
    void (*m_merge_callback) (Ob);

    mutable AssertSharedMutex m_mutex;
    typedef AssertSharedMutex::SharedLock SharedLock; // for const methods
    typedef AssertSharedMutex::UniqueLock UniqueLock; // for non-const methods

public:

    Carrier (size_t item_dim, void (*merge_callback) (Ob) = NULL);
    ~Carrier ();
    void move_from (const Carrier & other, const Ob * new2old);
    void validate () const;

    // attributes
    const DenseSet & support () const { return m_support; }
    size_t item_dim () const { return m_support.item_dim(); }
    size_t item_count () const { return m_item_count; }
    size_t rep_count () const { return m_rep_count; }
    bool contains (Ob ob) const { return m_support.contains(ob); }

    // relaxed operations
    Ob find (Ob ob) const;
    bool equal (Ob lhs, Ob rhs) const;
    Ob merge (Ob dep, Ob rep) const;
    Ob ensure_equal (Ob lhs, Ob rhs) const;
    Ob set_and_merge (
            Ob source,
            std::atomic<Ob> & destin) const; // return old val

    // strict operations
    Ob insert ();
    void remove (Ob ob);

private:

    Ob _find (Ob ob, Ob rep) const;
};

inline Ob Carrier::find (Ob ob) const
{
    SharedLock lock(m_mutex);
    POMAGMA_ASSERT5(contains(ob), "tried to find unsupported object " << ob);

    Ob rep = m_reps[ob].load(std::memory_order_relaxed);
    return rep == ob ? ob : _find(ob, rep);
}

inline bool Carrier::equal (Ob lhs, Ob rhs) const
{
    return find(lhs) == find(rhs);
}

inline Ob Carrier::ensure_equal (Ob lhs, Ob rhs) const
{
    if (lhs == rhs) {
        return lhs;
    } else {
        Ob dep = lhs > rhs ? lhs : rhs;
        Ob rep = lhs < rhs ? lhs : rhs;
        return merge(dep, rep);
    }
}

inline Ob Carrier::set_and_merge (
        Ob source,
        std::atomic<Ob> & destin) const
{
    POMAGMA_ASSERT_RANGE_(5, source, item_dim());

    Ob old = 0;
    while (not destin.compare_exchange_weak(
                old,
                source,
                std::memory_order_acq_rel,
                std::memory_order_acquire))
    {
        if (old == source) break;
        else if (source > old) { merge(source, old); break; }
        else { source = merge(old, source); }
    }
    return old;
}

} // namespace pomagma

#endif // POMAGMA_CARRIER_HPP
