#include "carrier.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

Carrier::Carrier (size_t item_dim)
    : m_support(item_dim),
      m_item_count(0),
      m_reps(alloc_blocks<Ob>(1 + item_dim))
{
    POMAGMA_DEBUG("creating Carrier with " << item_dim << " items");
    bzero(m_reps, sizeof(Ob) * (1 + item_dim));
}

void Carrier::move_from (
        const Carrier & other __attribute__((unused)),
        const Ob * new2old __attribute__((unused)))
{
    // TODO
}

Ob Carrier::insert () // WARNING not thread safe
{
    POMAGMA_ASSERT1(item_count() < item_dim(),
            "tried to insert in full Carrier");

    Ob ob = m_support.insert_one();
    m_reps[ob] = ob;
    return ob;
}

void Carrier::remove (Ob ob) // WARNING not thread safe
{
    POMAGMA_ASSERT2(m_support.contains(ob), "double removal: " << ob);
    POMAGMA_ASSERT2(m_reps[ob], "double removal: " << ob);

    Ob rep = m_reps[ob];
    if (rep == ob) {
        for (Ob other = ob + 1; other <= item_dim(); ++other) {
            POMAGMA_ASSERT2(m_reps[other] != ob, "removed a rep: " << ob);
        }
    } else {
        for (Ob other = ob + 1; other <= item_dim(); ++other) {
            if (m_reps[other] == ob) {
                m_reps[other] = rep;
            }
        }
    }

    m_support.remove(ob);
    m_reps[ob] = 0;
}

//----------------------------------------------------------------------------
// Merge trees

Ob Carrier::_find (Ob & ob) const
{
    return ob = find(m_reps[ob]); // ATOMIC
}

void Carrier::validate () const
{
    m_support.validate();

    for (Ob i = 1; i <= item_dim(); ++i) {
        if (contains(i)) {
            POMAGMA_ASSERT(m_reps[i], "supported object has no rep: " << i);
            POMAGMA_ASSERT(m_reps[i] <= i,
                "rep out of order: " << m_reps[i] << "," << i);
        } else {
            POMAGMA_ASSERT(m_reps[i] == 0, "unsupported object has rep: " << i);
        }
    }
}

} // namespace pomagma
