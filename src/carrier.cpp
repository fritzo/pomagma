#include "carrier.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

Carrier::Carrier (size_t item_dim)
    : m_support(item_dim),
      m_item_count(0),
      m_rep_count(0),
      m_reps(alloc_blocks<Rep>(1 + item_dim))
{
    POMAGMA_DEBUG("creating Carrier with " << item_dim << " items");
    for (Ob ob = 0; ob <= item_dim; ++ob) {
        new (&m_reps[ob]) Rep(0);
    }
}

Carrier::~Carrier ()
{
    for (Ob ob = 0; ob <= item_dim(); ++ob) {
        m_reps[ob].~Rep();
    }
    free_blocks(m_reps);
}

void Carrier::move_from (
        const Carrier & other,
        const Ob * new2old __attribute__((unused)))
{
    UniqueLock lock(m_mutex);

    m_item_count = other.m_item_count;
    m_rep_count = other.m_rep_count;
    TODO("move from other")
}

Ob Carrier::insert ()
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT1(item_count() < item_dim(),
            "tried to insert in full Carrier");

    Ob ob = m_support.insert_one();
    m_reps[ob] = ob;
    ++m_item_count;
    ++m_rep_count;
    return ob;
}

void Carrier::insert (Ob ob)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT1(not contains(ob), "double insertion: " << ob);
    POMAGMA_ASSERT1(not m_reps[ob], "double insertion: " << ob);

    m_support.insert(ob);
    m_reps[ob] = ob;
    ++m_item_count;
    ++m_rep_count;
}

void Carrier::remove (Ob ob)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT2(m_support.contains(ob), "double removal: " << ob);
    POMAGMA_ASSERT2(m_reps[ob], "double removal: " << ob);

    Ob rep = m_reps[ob];
    if (rep == ob) {
        for (Ob other = ob + 1; other <= item_dim(); ++other) {
            POMAGMA_ASSERT2(m_reps[other] != ob, "removed a rep: " << ob);
        }
        --m_rep_count;
    } else {
        for (Ob other = ob + 1; other <= item_dim(); ++other) {
            if (m_reps[other] == ob) {
                m_reps[other] = rep;
            }
        }
    }

    m_support.remove(ob);
    m_reps[ob] = 0;
    --m_item_count;
}

bool Carrier::merge (Ob dep, Ob rep) const
{
    SharedLock lock(m_mutex);

    POMAGMA_ASSERT2(dep > rep,
            "out of order merge: " << dep << "," << rep);
    POMAGMA_ASSERT2(m_support.contains(dep), "bad merge dep " << dep);
    POMAGMA_ASSERT2(m_support.contains(rep), "bad merge rep " << rep);

    while (not m_reps[dep].compare_exchange_weak(dep, rep)) {
        rep = m_reps[rep];
        if (dep == rep) return false;
        if (dep < rep) std::swap(dep, rep);
    }
    --m_rep_count;
    return true;
}

Ob Carrier::_find (Ob ob, Ob rep) const
{
    Ob rep_rep = find(rep);
    if (m_reps[ob].compare_exchange_weak(rep, rep_rep)) {
        return rep_rep;
    } else {
        return rep < rep_rep ? rep : rep_rep;
    }
}

void Carrier::validate () const
{
    SharedLock lock(m_mutex);

    m_support.validate();

    size_t actual_item_count = 0;
    size_t actual_rep_count = 0;
    for (Ob i = 1; i <= item_dim(); ++i) {
        if (contains(i)) {
            POMAGMA_ASSERT(m_reps[i], "supported object has no rep: " << i);
            POMAGMA_ASSERT(m_reps[i] <= i,
                "rep out of order: " << m_reps[i] << "," << i);
            ++actual_item_count;
            if (find(i) == i) {
                ++actual_rep_count;
            }
        } else {
            POMAGMA_ASSERT(m_reps[i] == 0, "unsupported object has rep: " << i);
        }
    }
    POMAGMA_ASSERT_EQ(item_count(), actual_item_count);
    POMAGMA_ASSERT_EQ(rep_count(), actual_rep_count);
}

} // namespace pomagma
