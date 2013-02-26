#pragma once

#include <pomagma/grower/util.hpp>
#include <pomagma/util/concurrent_dense_set.hpp>
#include <pomagma/util/threading.hpp>
//#include <functional>
//#include <algorithm>
#include <atomic>

namespace pomagma
{

class Carrier : noncopyable
{
    mutable DenseSet m_support;
    mutable std::atomic<size_t> m_item_count;
    mutable std::atomic<size_t> m_rep_count;
    typedef std::atomic<Ob> Rep;
    Rep * const m_reps;
    void (*m_insert_callback) (Ob);
    void (*m_merge_callback) (Ob);

    mutable AssertSharedMutex m_mutex;
    typedef AssertSharedMutex::SharedLock SharedLock; // for const methods
    typedef AssertSharedMutex::UniqueLock UniqueLock; // for non-const methods

public:

    Carrier (
        size_t item_dim,
        void (*insert_callback) (Ob) = nullptr,
        void (*merge_callback) (Ob) = nullptr);
    ~Carrier ();
    void validate () const;
    void log_stats () const;

    // attributes
    const DenseSet & support () const { return m_support; }
    size_t item_dim () const { return m_support.item_dim(); }
    size_t item_count () const { return m_item_count; }
    size_t rep_count () const { return m_rep_count; }
    bool contains (Ob ob) const { return m_support.contains(ob); }

    // raw operations
    void clear ();
    void raw_insert (Ob ob);
    void update ();

    // relaxed operations
    Ob find (Ob ob) const;
    bool equal (Ob lhs, Ob rhs) const;
    Ob merge (Ob dep, Ob rep) const;
    Ob ensure_equal (Ob lhs, Ob rhs) const;
    // these return true if value was set
    bool set_and_merge (std::atomic<Ob> & destin, Ob source) const;
    bool set_or_merge (std::atomic<Ob> & destin, Ob source) const;
    DenseSet::Iterator iter () const { return m_support.iter(); }
    Ob try_insert () const;

    // strict operations
    void unsafe_remove (const Ob ob);

private:

    Ob _find (Ob ob, Ob rep) const;
};

inline void Carrier::raw_insert (Ob ob)
{
    m_support.insert(ob, relaxed);
    m_reps[ob].store(ob, relaxed);
}

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

inline bool Carrier::set_and_merge (std::atomic<Ob> & destin, Ob source) const
{
    POMAGMA_ASSERT_RANGE_(5, source, item_dim());

    Ob old = 0;
    while (not destin.compare_exchange_strong(
                old,
                source,
                std::memory_order_acq_rel,
                std::memory_order_acquire))
    {
        source = ensure_equal(source, old);
        if (old == source) return false;
    }
    return old == 0;
}

inline bool Carrier::set_or_merge (std::atomic<Ob> & destin, Ob source) const
{
    POMAGMA_ASSERT_RANGE_(5, source, item_dim());

    Ob old = 0;
    if (destin.compare_exchange_strong(
                old,
                source,
                std::memory_order_acq_rel,
                std::memory_order_acquire))
    {
        return true;
    } else {
        ensure_equal(source, old);
        return false;
    }
}

} // namespace pomagma
