#pragma once

#include "util.hpp"
#include <pomagma/util/sequential_dense_set.hpp>
#include <pomagma/util/threading.hpp>
#include <atomic>

namespace pomagma
{

class Carrier : noncopyable
{
    DenseSet m_support;
    size_t m_item_count;
    mutable size_t m_rep_count;
    Ob * const m_reps;
    void (*m_merge_callback) (Ob);

public:

    Carrier (
        size_t item_dim,
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

    // safe operations
    Ob find (Ob ob) const;
    bool equal (Ob lhs, Ob rhs) const;
    Ob merge (Ob dep, Ob rep);
    Ob ensure_equal (Ob lhs, Ob rhs);
    // these return true if value was set
    bool set_and_merge (Ob & destin, Ob source); // if destin is nonzero
    bool set_or_merge (Ob & destin, Ob source); //  if destin is possibly zero
    DenseSet::Iterator iter () { return m_support.iter(); }
    Ob insert ();

    // unsafe operations
    void unsafe_remove (const Ob ob);

private:

    Ob _find (Ob ob, Ob rep) const;
};

inline void Carrier::raw_insert (Ob ob)
{
    m_support.insert(ob);
    m_reps[ob] = ob;
}

inline Ob Carrier::find (Ob ob) const
{
    POMAGMA_ASSERT5(contains(ob), "tried to find unsupported object " << ob);

    Ob rep = m_reps[ob];
    return rep == ob ? ob : _find(ob, rep);
}

inline bool Carrier::equal (Ob lhs, Ob rhs) const
{
    return find(lhs) == find(rhs);
}

inline Ob Carrier::ensure_equal (Ob lhs, Ob rhs)
{
    if (lhs == rhs) {
        return lhs;
    } else {
        Ob dep = lhs > rhs ? lhs : rhs;
        Ob rep = lhs < rhs ? lhs : rhs;
        return merge(dep, rep);
    }
}

inline bool Carrier::set_and_merge (Ob & destin, Ob source)
{
    if (destin == source) {
        return false;
    } else {
        destin = ensure_equal(destin, source);
        return true;
    }
}

inline bool Carrier::set_or_merge (Ob & destin, Ob source)
{
    if (destin) {
        ensure_equal(destin, source);
        return false;
    } else {
        destin = source;
        return true;
    }
}

} // namespace pomagma
