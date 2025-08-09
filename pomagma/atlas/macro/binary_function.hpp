#pragma once

#include <mutex>
#include <pomagma/util/sequential/dense_set.hpp>

#include "base_bin_rel.hpp"
#include "util.hpp"

namespace pomagma {

class BinaryFunction : noncopyable {
    mutable base_bin_rel m_lines;
    mutable ObPairMap m_values;
    mutable std::mutex m_raw_mutex;

   public:
    explicit BinaryFunction(Carrier& carrier);
    BinaryFunction(Carrier& carrier, BinaryFunction&& other);
    void validate() const;
    void log_stats(const std::string& prefix) const;

    // raw operations
    static bool is_symmetric() { return false; }
    size_t count_pairs() const { return m_values.size(); }
    void raw_lock() { m_raw_mutex.lock(); }
    void raw_insert(Ob lhs, Ob rhs, Ob val);  // lock to concurrently write
    void raw_unlock() { m_raw_mutex.unlock(); }
    void update() {}
    void clear();

    // safe operations
    // m_values is source of truth; m_lines lag
    DenseSet get_Lx_set(Ob lhs) const { return m_lines.Lx_set(lhs); }
    DenseSet get_Rx_set(Ob rhs) const { return m_lines.Rx_set(rhs); }
    bool defined(Ob lhs, Ob rhs) const;
    Ob find(Ob lhs, Ob rhs) const;
    Ob raw_find(Ob lhs, Ob rhs) const { return find(lhs, rhs); }
    DenseSet::Iterator iter_lhs(Ob lhs) const;
    DenseSet::Iterator iter_rhs(Ob rhs) const;
    void insert(Ob lhs, Ob rhs, Ob val) const;
    void update_values() const;  // postcondition: all values are reps

    // safe thread-locally queued operations
    void lazy_insert(Ob lhs, Ob rhs, Ob val) const;
    void lazy_equate(Ob lhs1, Ob rhs1, Ob lhs2, Ob rhs2) const;
    void lazy_gather() const;   // called by worker threads
    size_t lazy_flush() const;  // called by main thread

    // unsafe operations
    void unsafe_merge(const Ob dep);

   private:
    const Carrier& carrier() const { return m_lines.carrier(); }
    const DenseSet& support() const { return m_lines.support(); }
    size_t item_dim() const { return support().item_dim(); }

    struct Queue {
        Queue() { clear(); }
        std::vector<std::tuple<Ob, Ob, Ob>> m_tasks;
        void insert(Ob lhs, Ob rhs, Ob val);
        void clear();
        void process_mergers(const Carrier& carrier);
    };
    Queue& worker_consequents() const;
    mutable Queue m_consequents;
    mutable std::mutex m_consequents_mutex;
    static thread_local std::unordered_map<const BinaryFunction*, Queue>*
        s_consequents;
};

inline bool BinaryFunction::defined(Ob lhs, Ob rhs) const {
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    return m_lines.get_Lx(lhs, rhs);
}

inline Ob BinaryFunction::find(Ob lhs, Ob rhs) const {
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    auto i = m_values.find(std::make_pair(lhs, rhs));
    return i == m_values.end() ? 0 : i->second;
    // if (i == m_values.end()) {
    //    return 0;
    //} else {
    //    Ob & val = i->second;
    //    Ob rep = carrier().find(val);
    //    if (rep != val) {
    //        val = rep;
    //    }
    //    return rep;
    //}
}

inline DenseSet::Iterator BinaryFunction::iter_lhs(Ob lhs) const {
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    return DenseSet::Iterator(item_dim(), m_lines.Lx(lhs));
}

inline DenseSet::Iterator BinaryFunction::iter_rhs(Ob rhs) const {
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    return DenseSet::Iterator(item_dim(), m_lines.Rx(rhs));
}

inline void BinaryFunction::raw_insert(Ob lhs, Ob rhs, Ob val) {
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    m_values.insert(std::make_pair(std::make_pair(lhs, rhs), val));
    m_lines.Lx(lhs, rhs).one();
    m_lines.Rx(lhs, rhs).one();
}

inline void BinaryFunction::insert(Ob lhs, Ob rhs, Ob val) const {
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    Ob& val_ref = m_values[std::make_pair(lhs, rhs)];
    if (val_ref) {
        carrier().set_and_merge(val_ref, val);
    } else {
        val_ref = val;
        m_lines.Lx(lhs, rhs).one();
        m_lines.Rx(lhs, rhs).one();
    }
}

inline void BinaryFunction::lazy_insert(Ob lhs, Ob rhs, Ob val) const {
    worker_consequents().insert(lhs, rhs, val);
}

inline void BinaryFunction::lazy_equate(Ob lhs1, Ob rhs1, Ob lhs2,
                                        Ob rhs2) const {
    Ob val1 = find(lhs1, rhs1);
    Ob val2 = find(lhs2, rhs2);
    if (likely(val1 == val2)) return;
    if (val2 == 0 or (val1 != 0 and val2 > val1)) {
        lazy_insert(lhs2, rhs2, val1);
    } else {
        lazy_insert(lhs1, rhs1, val2);
    }
}

inline BinaryFunction::Queue& BinaryFunction::worker_consequents() const {
    if (unlikely(s_consequents == nullptr)) {
        // never freed
        s_consequents = new std::unordered_map<const BinaryFunction*, Queue>;
    }
    return (*s_consequents)[this];
}

inline void BinaryFunction::Queue::insert(Ob lhs, Ob rhs, Ob val) {
    m_tasks.emplace_back(lhs, rhs, val);
}

}  // namespace pomagma
