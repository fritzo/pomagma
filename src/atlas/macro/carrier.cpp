#include "carrier.hpp"
#include <pomagma/util/aligned_alloc.hpp>
#include <cstring>

#define POMAGMA_DEBUG1(message) POMAGMA_DEBUG(message)

namespace pomagma
{

Carrier::Carrier (
        size_t item_dim,
        void (*merge_callback) (Ob))
    : m_support(item_dim),
      m_item_count(0),
      m_rep_count(0),
      m_reps(alloc_blocks<Ob>(1 + item_dim)),
      m_merge_callback(merge_callback)
{
    POMAGMA_DEBUG("creating Carrier with " << item_dim << " items");
    POMAGMA_ASSERT_LE(item_dim, MAX_ITEM_DIM);
    construct_blocks(m_reps, 1 + item_dim, 0);
}

Carrier::Carrier (
        size_t item_dim,
        const Carrier & other)
    : m_support(item_dim),
      m_item_count(0),
      m_rep_count(0),
      m_reps(alloc_blocks<Ob>(1 + item_dim)),
      m_merge_callback(other.m_merge_callback)
{
    POMAGMA_DEBUG("resizing Carrier with " << item_dim << " items");
    POMAGMA_ASSERT_LE(item_dim, MAX_ITEM_DIM);
    construct_blocks(m_reps, 1 + item_dim, 0);

    POMAGMA_ASSERT_EQ(other.item_count(), other.rep_count());
    for (auto iter = other.iter(); iter.ok(); iter.next()) {
        Ob ob = * iter;
        POMAGMA_ASSERT_LE(ob, m_support.item_dim());
        raw_insert(ob);
    }
    update();
}

Carrier::~Carrier ()
{
    destroy_blocks(m_reps, 1 + item_dim());
    free_blocks(m_reps);
}

void Carrier::clear ()
{
    m_support.zero();
    zero_blocks(m_reps, 1 + item_dim());
    m_rep_count = 0;
    m_item_count = 0;
}

void Carrier::update ()
{
    m_rep_count = m_item_count = m_support.count_items();
}

Ob Carrier::unsafe_insert ()
{
    POMAGMA_ASSERT_LT(item_count(), item_dim());
    Ob ob = m_support.insert_one();
    m_reps[ob] = ob;
    ++m_item_count;
    ++m_rep_count;
    //POMAGMA_DEBUG1(m_item_count << " obs after inserting " << ob);
    return ob;
}

void Carrier::unsafe_remove (const Ob ob)
{
    POMAGMA_ASSERT2(m_support.contains(ob), "double removal: " << ob);
    Ob rep = ob;
    while (m_reps[rep] != rep) {
        rep = m_reps[rep];
    }
    POMAGMA_ASSERT2(rep, "double removal: " << ob);
    if (rep == ob) {
        for (Ob other = ob + 1, end = item_dim(); other <= end; ++other) {
            POMAGMA_ASSERT2(m_reps[other] != ob,
                    "removed rep " << ob << " before dep " << other);
        }
        --m_rep_count;
    } else {
        for (Ob other = ob + 1, end = item_dim(); other <= end; ++other) {
            if (m_reps[other] == ob) {
                m_reps[other] = rep;
            }
        }
    }

    m_support.remove(ob);
    m_reps[ob] = 0;
    --m_item_count;
    POMAGMA_DEBUG1(m_item_count << " obs after removing " << ob);
}

Ob Carrier::merge (Ob dep, Ob rep) const
{
    POMAGMA_ASSERT2(dep > rep,
            "out of order merge: " << dep << "," << rep);
    POMAGMA_ASSERT2(m_support.contains(dep), "bad merge dep " << dep);
    POMAGMA_ASSERT2(m_support.contains(rep), "bad merge rep " << rep);

    std::unique_lock<std::mutex> lock(m_merge_mutex);
    while (m_reps[dep] != dep) {
        dep = m_reps[dep];
        if (dep == rep) { return rep; }
        if (dep < rep) { std::swap(dep, rep); }
    }
    m_reps[dep] = rep;
    if (m_merge_callback) {
        m_merge_callback(dep);
    }
    --m_rep_count;
    POMAGMA_ASSERT2(m_rep_count, "no reps remain");
    return rep;
}

Ob Carrier::_find (Ob ob, Ob rep) const
{
    Ob rep_rep = find(rep);
    if (m_reps[ob] == rep_rep) {
        return rep_rep;
    } else {
        return rep < rep_rep ? rep : rep_rep;
    }
}

void Carrier::validate () const
{
    POMAGMA_INFO("Validating Carrier");

    m_support.validate();

    size_t actual_item_count = 0;
    size_t actual_rep_count = 0;
    for (Ob i = 1; i <= item_dim(); ++i) {
        Ob rep = m_reps[i];
        if (contains(i)) {
            POMAGMA_ASSERT(rep, "supported object has no rep: " << i);
            POMAGMA_ASSERT(rep <= i, "rep out of order: " << rep << "," << i);
            ++actual_item_count;
            if (rep == i) {
                ++actual_rep_count;
            }
        } else {
            POMAGMA_ASSERT(rep == 0, "unsupported object has rep: " << i);
        }
    }
    POMAGMA_ASSERT_EQ(item_count(), actual_item_count);
    POMAGMA_ASSERT_EQ(rep_count(), actual_rep_count);
}

void Carrier::log_stats () const
{
    const Carrier & carrier = * this;
    POMAGMA_PRINT(carrier.item_dim());
    POMAGMA_PRINT(carrier.item_count());
    POMAGMA_PRINT(carrier.rep_count());
}

} // namespace pomagma
