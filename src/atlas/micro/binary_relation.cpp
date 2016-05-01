#include "binary_relation.hpp"
#include <pomagma/util/aligned_alloc.hpp>
#include <cstring>

namespace pomagma {

static void noop_callback(Ob, Ob) {}

BinaryRelation::BinaryRelation(const Carrier& carrier,
                               void (*insert_callback)(Ob, Ob))
    : m_lines(carrier),
      m_insert_callback(insert_callback ? insert_callback : noop_callback) {
    POMAGMA_DEBUG("creating BinaryRelation with " << round_word_dim()
                                                  << " words");
}

BinaryRelation::~BinaryRelation() {}

void BinaryRelation::validate() const {
    UniqueLock lock(m_mutex);

    POMAGMA_INFO("Validating BinaryRelation");

    m_lines.validate();

    size_t num_pairs = 0;

    DenseSet Lx(round_item_dim(), nullptr);
    DenseSet Rx(round_item_dim(), nullptr);
    for (Ob i = 1; i <= item_dim(); ++i) {
        bool sup_i = supports(i);
        Lx.init(m_lines.Lx(i));

        for (Ob j = 1; j <= item_dim(); ++j) {
            bool sup_ij = sup_i and supports(j);
            Rx.init(m_lines.Rx(j));

            bool Lx_ij = Lx.contains(j);
            bool Rx_ij = Rx.contains(i);
            num_pairs += Rx_ij;

            POMAGMA_ASSERT(Lx_ij == Rx_ij, "Lx,Rx disagree at "
                                               << i << "," << j << ", Lx is "
                                               << Lx_ij << ", Rx is " << Rx_ij);

            POMAGMA_ASSERT(sup_ij or not Lx_ij, "Lx unsupported at " << i << ","
                                                                     << j);

            POMAGMA_ASSERT(sup_ij or not Rx_ij, "Rx unsupported at " << i << ","
                                                                     << j);
        }
    }

    size_t true_size = count_pairs();
    POMAGMA_ASSERT(num_pairs == true_size,
                   "incorrect number of pairs: " << num_pairs << " should be "
                                                 << true_size);
}

void BinaryRelation::validate_disjoint(const BinaryRelation& other) const {
    UniqueLock lock(m_mutex);

    POMAGMA_INFO("Validating disjoint pair of BinaryRelations");

    // validate supports agree
    POMAGMA_ASSERT_EQ(support().item_dim(), other.support().item_dim());
    POMAGMA_ASSERT_EQ(support().count_items(), other.support().count_items());
    POMAGMA_ASSERT(support() == other.support(),
                   "BinaryRelation supports differ");

    // validate disjointness
    DenseSet this_set(item_dim(), nullptr);
    DenseSet other_set(item_dim(), nullptr);
    for (auto i = support().iter(); i.ok(); i.next()) {
        this_set.init(m_lines.Lx(*i));
        other_set.init(other.m_lines.Lx(*i));
        POMAGMA_ASSERT(this_set.disjoint(other_set),
                       "BinaryRelations intersect at row " << *i);
    }
}

void BinaryRelation::log_stats(const std::string& prefix) const {
    m_lines.log_stats(prefix);
}

void BinaryRelation::update() {
    memory_barrier();
    m_lines.copy_Lx_to_Rx();
    memory_barrier();
}

void BinaryRelation::clear() {
    memory_barrier();
    m_lines.clear();
    memory_barrier();
}

void BinaryRelation::insert(Ob i, const DenseSet& js) {
    DenseSet diff(item_dim());
    DenseSet dest(item_dim(), m_lines.Lx(i));
    if (dest.ensure(js, diff)) {
        for (auto k = diff.iter(); k.ok(); k.next()) {
            _insert_Rx(i, *k);
            m_insert_callback(i, *k);
        }
    }
}

void BinaryRelation::insert(const DenseSet& is, Ob j) {
    DenseSet diff(item_dim());
    DenseSet dest(item_dim(), m_lines.Rx(j));
    if (dest.ensure(is, diff)) {
        for (auto k = diff.iter(); k.ok(); k.next()) {
            _insert_Lx(*k, j);
            m_insert_callback(*k, j);
        }
    }
}

void BinaryRelation::_remove_Lx(const DenseSet& is, Ob j) {
    // slower version
    // for (auto i = is.iter(); i.ok(); i.next()) {
    //    _remove_Lx(*i, j);
    //}

    // faster version
    Word mask = ~(Word(1) << (j % BITS_PER_WORD));
    size_t offset = j / BITS_PER_WORD;
    std::atomic<Word>* lines = m_lines.Lx() + offset;
    for (auto i = is.iter(); i.ok(); i.next()) {
        lines[*i * round_word_dim()].fetch_and(mask, relaxed);
    }
}

void BinaryRelation::_remove_Rx(Ob i, const DenseSet& js) {
    // slower version
    // for (auto j = js.iter(); j.ok(); j.next()) {
    //    _remove_Rx(i, *j);
    //}

    // faster version
    Word mask = ~(Word(1) << (i % BITS_PER_WORD));
    size_t offset = i / BITS_PER_WORD;
    std::atomic<Word>* lines = m_lines.Rx() + offset;
    for (auto j = js.iter(); j.ok(); j.next()) {
        lines[*j * round_word_dim()].fetch_and(mask, relaxed);
    }
}

// policy: callback whenever i~k but not j~k
void BinaryRelation::unsafe_merge(Ob i) {
    UniqueLock lock(m_mutex);

    Ob j = carrier().find(i);
    POMAGMA_ASSERT4(j < i, "BinaryRelation tried to merge item with self");

    DenseSet diff(item_dim());
    DenseSet rep(item_dim(), nullptr);
    DenseSet dep(item_dim(), nullptr);

    // merge rows (i, _) into (j, _)
    dep.init(m_lines.Lx(i));
    _remove_Rx(i, dep);
    rep.init(m_lines.Lx(j));
    if (rep.merge(dep, diff)) {
        for (auto k = diff.iter(); k.ok(); k.next()) {
            _insert_Rx(j, *k);
            m_insert_callback(j, *k);
        }
    }

    // merge cols (_, i) into (_, j)
    dep.init(m_lines.Rx(i));
    _remove_Lx(dep, i);
    rep.init(m_lines.Rx(j));
    if (rep.merge(dep, diff)) {
        for (auto k = diff.iter(); k.ok(); k.next()) {
            _insert_Lx(*k, j);
            m_insert_callback(*k, j);
        }
    }
}

}  // namespace pomagma
