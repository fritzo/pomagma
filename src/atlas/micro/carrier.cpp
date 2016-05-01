#include "carrier.hpp"
#include <pomagma/util/aligned_alloc.hpp>
#include <cstring>

#define POMAGMA_DEBUG1(message) POMAGMA_DEBUG(message)

namespace pomagma {

Carrier::Carrier(size_t item_dim, void (*insert_callback)(Ob),
                 void (*merge_callback)(Ob))
    : m_support(item_dim),
      m_item_count(0),
      m_rep_count(0),
      m_reps(alloc_blocks<Rep>(1 + item_dim)),
      m_insert_callback(insert_callback),
      m_merge_callback(merge_callback) {
    POMAGMA_DEBUG("creating Carrier with " << item_dim << " items");
    POMAGMA_ASSERT_LE(item_dim, MAX_ITEM_DIM);
    construct_blocks(m_reps, 1 + item_dim, 0);
}

Carrier::~Carrier() {
    destroy_blocks(m_reps, 1 + item_dim());
    free_blocks(m_reps);
}

void Carrier::clear() {
    memory_barrier();
    m_support.zero();
    zero_blocks(m_reps, 1 + item_dim());
    m_rep_count = 0;
    m_item_count = 0;
    memory_barrier();
}

void Carrier::update() {
    memory_barrier();
    m_rep_count = m_item_count = m_support.count_items();
    memory_barrier();
}

Ob Carrier::try_insert() const {
    SharedLock lock(m_mutex);

    while (item_count() < item_dim()) {
        for (Ob ob = 1, end = item_dim(); ob <= end; ++ob) {
            Ob zero = 0;
            // This could be optimized using m_support iteration.
            // See DenseSet::try_insert for example low-level code.
            bool inserted = m_reps[ob].compare_exchange_strong(
                zero, ob, std::memory_order_acq_rel, std::memory_order_acquire);
            if (unlikely(inserted)) {
                m_support.insert(ob, std::memory_order_release);
                ++m_item_count;
                ++m_rep_count;
                if (m_insert_callback) {
                    m_insert_callback(ob);
                }
                // The following triggers a weird gcc bug or something
                // error: invalid memory model for ‘__atomic_load
                // POMAGMA_DEBUG1(m_item_count.load() << " obs after insert()");
                return ob;
            }
        }
    }

    return 0;
}

void Carrier::unsafe_remove(const Ob ob) {
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT2(m_support.contains(ob), "double removal: " << ob);
    Ob rep = ob;
    while (not m_reps[rep].compare_exchange_strong(rep, rep)) {
    }
    POMAGMA_ASSERT2(rep, "double removal: " << ob);
    if (rep == ob) {
        for (Ob other = ob + 1, end = item_dim(); other <= end; ++other) {
            POMAGMA_ASSERT2(m_reps[other].load() != ob,
                            "removed rep " << ob << " before dep " << other);
        }
        --m_rep_count;
    } else {
        for (Ob other = ob + 1, end = item_dim(); other <= end; ++other) {
            Ob expected = ob;
            m_reps[other].compare_exchange_strong(expected, rep);
        }
    }

    m_support.remove(ob);
    m_reps[ob].store(0);
    --m_item_count;
    POMAGMA_DEBUG1(m_item_count.load() << " obs after remove()");
}

Ob Carrier::merge(Ob dep, Ob rep) const {
    SharedLock lock(m_mutex);

    POMAGMA_ASSERT2(dep > rep, "out of order merge: " << dep << "," << rep);
    POMAGMA_ASSERT2(m_support.contains(dep), "bad merge dep " << dep);
    POMAGMA_ASSERT2(m_support.contains(rep), "bad merge rep " << rep);

    while (not m_reps[dep].compare_exchange_weak(
        dep, rep, std::memory_order_acq_rel, std::memory_order_acquire)) {
        rep = m_reps[rep].load(std::memory_order_acquire);
        if (dep == rep) return rep;
        if (dep < rep) std::swap(dep, rep);
    }
    if (m_merge_callback) {
        m_merge_callback(dep);
    }
    --m_rep_count;
    return rep;
}

Ob Carrier::_find(Ob ob, Ob rep) const {
    Ob rep_rep = find(rep);
    if (m_reps[ob].compare_exchange_weak(rep, rep_rep,
                                         std::memory_order_acq_rel,
                                         std::memory_order_acquire)) {
        return rep_rep;
    } else {
        return rep < rep_rep ? rep : rep_rep;
    }
}

void Carrier::validate() const {
    UniqueLock lock(m_mutex);

    POMAGMA_INFO("Validating Carrier");

    m_support.validate();

    size_t actual_item_count = 0;
    size_t actual_rep_count = 0;
    for (Ob i = 1; i <= item_dim(); ++i) {
        Ob rep = m_reps[i].load();
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

void Carrier::log_stats() const {
    const Carrier& carrier = *this;
    POMAGMA_PRINT(carrier.item_dim());
    POMAGMA_PRINT(carrier.item_count());
    POMAGMA_PRINT(carrier.rep_count());
}

}  // namespace pomagma
