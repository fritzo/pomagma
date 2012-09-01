#ifndef POMAGMA_CARRIER_HPP
#define POMAGMA_CARRIER_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include <functional>
#include <algorithm>
//#include <boost/thread/mutex.hpp>
//#include <boost/thread/shared_mutex.hpp>
//#include <boost/thread/locks.hpp>

namespace pomagma
{

// WARNING nonstandard use of constness:
// insert, find are const
// merge, remove are nonconst

class Carrier
{
    DenseSet m_support;
    size_t m_item_count;
    size_t m_rep_count;
    Ob * const m_reps;

public:

    Carrier (size_t item_dim = 511);
    void move_from (const Carrier & other, const Ob * new2old);

    const DenseSet & support () const { return m_support; }
    size_t item_dim () const { return m_support.item_dim(); }
    size_t item_count () const { return m_item_count; }
    size_t rep_count () const { return m_rep_count; }
    bool contains (Ob ob) const { return m_support.contains(ob); }

    // merge trees
private:
    Ob _find (Ob & ob) const;
public:
    Ob find (Ob ob) const
    {
        POMAGMA_ASSERT5(contains(ob),
                "tried to find unsupported object " << ob);
        Ob & rep = m_reps[ob];
        return rep == ob ? ob : _find(rep);
        // TODO this could be more clever
    }

    bool equivalent (Ob lhs, Ob rhs) const
    {
        return find(lhs) == find(rhs);
    }

    void insert (Ob ob) // WARNING not thread safe
    {
        POMAGMA_ASSERT1(not contains(ob), "double insertion: " << ob);
        POMAGMA_ASSERT1(not m_reps[ob], "double insertion: " << ob);

        m_support.insert(ob);
        m_reps[ob] = ob;
    }

    Ob insert (); // WARNING not thread safe

    void remove (Ob ob); // WARNING not thread safe

    void merge (Ob dep, Ob rep) const
    {
        POMAGMA_ASSERT2(dep > rep,
                "out of order merge: " << dep << "," << rep);
        POMAGMA_ASSERT2(m_support.contains(dep), "bad merge dep " << dep);
        POMAGMA_ASSERT2(m_support.contains(rep), "bad merge rep " << rep);

        m_reps[find(dep)] = find(rep); // ATOMIC
    }

    void validate () const;
};

} // namespace pomagma

#endif // POMAGMA_CARRIER_HPP
