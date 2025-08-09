#pragma once

#include <pomagma/util/sequential/dense_set.hpp>

#include "base_bin_rel.hpp"
#include "util.hpp"

namespace pomagma {

class BinaryRelation : noncopyable {
    // DEPRECATED
    mutable base_bin_rel m_lines;

    // TODO
    // use a single 1-bit-per-entry 32x32-tiled representation
    // following the block math in surveyor/binary_function

   public:
    explicit BinaryRelation(const Carrier& carrier);
    BinaryRelation(const Carrier& carrier, BinaryRelation&& other);
    ~BinaryRelation();
    void validate() const;
    void validate_disjoint(const BinaryRelation& other) const;
    void log_stats(const std::string& prefix) const;
    size_t count_pairs() const { return m_lines.count_pairs(); }

    // raw operations
    size_t item_dim() const { return m_lines.item_dim(); }
    size_t round_word_dim() const { return m_lines.round_word_dim(); }
    const Word* raw_data() const { return m_lines.Lx(); }
    Word* raw_data() { return m_lines.Lx(); }
    void update() { m_lines.copy_Lx_to_Rx(); }
    void clear() { m_lines.clear(); }

    // safe operations
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

    // safe thread-locally queued operations
    void lazy_insert(Ob i, Ob j) const;
    void lazy_try_insert(Ob i, Ob j) const;
    void lazy_gather() const;
    size_t lazy_flush();

    // unsafe operations
    void unsafe_merge(Ob dep);
    void process_mergers();

   private:
    const Carrier& carrier() const { return m_lines.carrier(); }
    const DenseSet& support() const { return m_lines.support(); }
    bool supports(Ob i) const { return support().contains(i); }
    bool supports(Ob i, Ob j) const { return supports(i) and supports(j); }

    size_t word_dim() const { return m_lines.word_dim(); }
    size_t round_item_dim() const { return m_lines.round_item_dim(); }
    size_t data_size_words() const { return m_lines.data_size_words(); }

    struct Queue {
        using HighPair = std::pair<ObHigh, ObHigh>;
        using LowQueue = std::vector<std::pair<ObLow, ObLow>>;
        std::unordered_map<HighPair, LowQueue, ObPairHash> m_tasks;
        std::vector<HighPair> m_index;
        void insert(Ob i, Ob j) noexcept;
        void clear();
        // methods for processing tiles of (i,j) pairs
        void build_index();
        size_t task_count() const { return m_tasks.size(); }
        std::pair<HighPair, const LowQueue&> get_task(size_t i) const noexcept;
        void process_mergers(const Carrier& carrier);
    };
    Queue& worker_consequents() const;
    mutable Queue m_consequents;
    mutable std::mutex m_consequents_mutex;
    static thread_local std::unordered_map<const BinaryRelation*, Queue>*
        s_consequents;

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
    }
}

inline void BinaryRelation::insert_Rx(Ob i, Ob j) {
    if (not m_lines.Rx(i, j).fetch_one()) {
        _insert_Lx(i, j);
    }
}

inline void BinaryRelation::lazy_insert(Ob i, Ob j) const {
    worker_consequents().insert(i, j);
}

inline void BinaryRelation::lazy_try_insert(Ob i, Ob j) const {
    if (likely(find(i, j))) return;
    lazy_insert(i, j);
}

inline void BinaryRelation::Queue::insert(Ob i, Ob j) noexcept {
    auto [i_hi, i_lo] = ob_to_hi_lo(i);
    auto [j_hi, j_lo] = ob_to_hi_lo(j);
    m_tasks[std::make_pair(i_hi, j_hi)].emplace_back(i_lo, j_lo);
}

inline BinaryRelation::Queue& BinaryRelation::worker_consequents() const {
    if (unlikely(s_consequents == nullptr)) {
        // never freed
        s_consequents = new std::unordered_map<const BinaryRelation*, Queue>;
    }
    return (*s_consequents)[this];
}

inline std::pair<BinaryRelation::Queue::HighPair,
                 const BinaryRelation::Queue::LowQueue&>
BinaryRelation::Queue::get_task(size_t i) const noexcept {
    HighPair hi = m_index.at(i);
    const LowQueue& lo_queue = m_tasks.find(hi)->second;
    return {hi, lo_queue};
}

}  // namespace pomagma
