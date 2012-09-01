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
    size_t m_item_count;
    mutable size_t m_rep_count;
    typedef std::atomic<Ob> Rep;
    Rep * const m_reps;

    mutable AssertSharedMutex m_mutex;
    typedef AssertSharedMutex::SharedLock SharedLock;
    typedef AssertSharedMutex::UniqueLock UniqueLock;

public:

    Carrier (size_t item_dim = DEFAULT_ITEM_DIM);
    ~Carrier ();
    void move_from (const Carrier & other, const Ob * new2old);

    // attributes
    const DenseSet & support () const { return m_support; }
    size_t item_dim () const { return m_support.item_dim(); }
    size_t item_count () const { return m_item_count; }
    size_t rep_count () const { return m_rep_count; }
    bool contains (Ob ob) const { return m_support.contains(ob); }

    // non-blocking interface
    Ob find (Ob ob) const;
    bool equivalent (Ob lhs, Ob rhs) const;
    bool merge (Ob dep, Ob rep) const; // return true if not already merged
    void validate () const;

    // blocking
    Ob insert ();
    void insert (Ob ob);
    void remove (Ob ob);

private:

    Ob _find (Ob ob, Ob rep) const;
};

inline Ob Carrier::find (Ob ob) const
{
    SharedLock lock(m_mutex);
    POMAGMA_ASSERT5(contains(ob), "tried to find unsupported object " << ob);
    Ob rep = m_reps[ob];
    return rep == ob ? ob : _find(ob, rep);
}

inline bool Carrier::equivalent (Ob lhs, Ob rhs) const
{
    return find(lhs) == find(rhs);
}

} // namespace pomagma

#endif // POMAGMA_CARRIER_HPP
