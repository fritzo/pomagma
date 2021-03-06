#pragma once

#include "util.hpp"
#include "base_bin_rel.hpp"
#include <pomagma/util/concurrent/dense_set.hpp>

namespace pomagma {

// a pair of dense sets of dense sets, one col-row, one row-col
class BinaryRelation : noncopyable {
    mutable base_bin_rel m_lines;
    void (*m_insert_callback)(Ob, Ob);

    mutable SharedMutex m_mutex;
    typedef SharedMutex::SharedLock SharedLock;
    typedef SharedMutex::UniqueLock UniqueLock;

   public:
    BinaryRelation(const Carrier& carrier,
                   void (*insert_callback)(Ob, Ob) = nullptr);
    ~BinaryRelation();
    void validate() const;
    void validate_disjoint(const BinaryRelation& other) const;
    void log_stats(const std::string& prefix) const;
    size_t count_pairs() const { return m_lines.count_pairs(); }

    // raw operations
    size_t item_dim() const { return m_lines.item_dim(); }
    size_t round_word_dim() const { return m_lines.round_word_dim(); }
    const std::atomic<Word>* raw_data() const { return m_lines.Lx(); }
    std::atomic<Word>* raw_data() { return m_lines.Lx(); }
    void update();
    void clear();

    // relaxed operations
    DenseSet get_Lx_set(Ob lhs) const { return m_lines.Lx_set(lhs); }
    DenseSet get_Rx_set(Ob rhs) const { return m_lines.Rx_set(rhs); }
    bool find_Lx(Ob i, Ob j) const { return m_lines.get_Lx(i, j); }
    bool find_Rx(Ob i, Ob j) const { return m_lines.get_Rx(i, j); }
    bool find(Ob i, Ob j) const { return find_Lx(i, j); }
    DenseSet::Iterator iter_lhs(Ob lhs) const;
    DenseSet::Iterator iter_rhs(Ob rhs) const;
    void insert_Lx(Ob i, Ob j);
    void insert_Rx(Ob i, Ob j);
    void insert(Ob i, Ob j) { return insert_Lx(i, j); }
    void insert(Ob i, const DenseSet& js);
    void insert(const DenseSet& is, Ob j);

    // strict operations
    void unsafe_merge(Ob dep);

   private:
    const Carrier& carrier() const { return m_lines.carrier(); }
    const DenseSet& support() const { return m_lines.support(); }
    bool supports(Ob i) const { return support().contains(i); }
    bool supports(Ob i, Ob j) const { return supports(i) and supports(j); }

    size_t word_dim() const { return m_lines.word_dim(); }
    size_t round_item_dim() const { return m_lines.round_item_dim(); }
    size_t data_size_words() const { return m_lines.data_size_words(); }

    void _insert(Ob i, Ob j) {
        _insert_Lx(i, j);
        _insert_Rx(i, j);
    }
    void _insert_Lx(Ob i, Ob j) { m_lines.Lx(i, j).one(); }
    void _insert_Rx(Ob i, Ob j) { m_lines.Rx(i, j).one(); }
    void _remove_Lx(Ob i, Ob j) { m_lines.Lx(i, j).zero(); }
    void _remove_Rx(Ob i, Ob j) { m_lines.Rx(i, j).zero(); }
    void _remove_Lx(const DenseSet& is, Ob i);
    void _remove_Rx(Ob i, const DenseSet& js);
};

inline DenseSet::Iterator BinaryRelation::iter_lhs(Ob lhs) const {
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    return DenseSet::Iterator(item_dim(), m_lines.Lx(lhs));
}

inline DenseSet::Iterator BinaryRelation::iter_rhs(Ob rhs) const {
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    return DenseSet::Iterator(item_dim(), m_lines.Rx(rhs));
}

inline void BinaryRelation::insert_Lx(Ob i, Ob j) {
    if (not m_lines.Lx(i, j).fetch_one()) {
        _insert_Rx(i, j);
        m_insert_callback(i, j);
    }
}

inline void BinaryRelation::insert_Rx(Ob i, Ob j) {
    if (not m_lines.Rx(i, j).fetch_one()) {
        _insert_Lx(i, j);
        m_insert_callback(i, j);
    }
}

}  // namespace pomagma
