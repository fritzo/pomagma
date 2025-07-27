#pragma once

#include <pomagma/util/sequential/dense_set.hpp>

#include "carrier.hpp"
#include "util.hpp"

namespace pomagma {

class InjectiveFunction : noncopyable {
    const Carrier& m_carrier;
    DenseSet m_set;
    DenseSet m_inverse_set;
    Ob* const m_values;
    Ob* const m_inverse;

   public:
    explicit InjectiveFunction(const Carrier& carrier);
    InjectiveFunction(const Carrier& carrier, InjectiveFunction&& other);
    ~InjectiveFunction();
    void validate() const;
    void log_stats(const std::string& prefix) const;

    // raw operations
    size_t count_items() const { return m_set.count_items(); }
    Ob raw_find(Ob key) const;
    void raw_insert(Ob key, Ob val);
    void update() {}
    void clear();

    // relaxed operations
    // m_values & m_inverse are source of truth; m_set & m_inverse_set lag
    const DenseSet& defined() const { return m_set; }
    const DenseSet& inverse_defined() const { return m_inverse_set; }
    bool defined(Ob key) const;
    bool inverse_defined(Ob key) const;
    Ob find(Ob key) const;
    Ob inverse_find(Ob val) const;
    DenseSet::Iterator iter() const { return m_set.iter(); }
    DenseSet::Iterator inverse_iter() const { return m_inverse_set.iter(); }
    void insert(Ob key, Ob val);
    void update_values() const {}  // postcondition: all values are reps

    // safe thread-locally queued operations
    void lazy_insert(Ob key, Ob val) const;
    void lazy_gather() const;
    size_t lazy_flush();

    // strict operations
    void unsafe_merge(Ob dep);

   private:
    const DenseSet& support() const { return m_carrier.support(); }
    size_t item_dim() const { return support().item_dim(); }

    struct Queue {
        std::vector<std::pair<Ob, Ob>> m_tasks;
        void insert(Ob key, Ob val) { m_tasks.emplace_back(key, val); }
        void clear() { std::vector<std::pair<Ob, Ob>>().swap(m_tasks); }
    };
    Queue& worker_queue() const;
    mutable Queue m_queue;
    mutable std::mutex m_queue_mutex;
    static thread_local std::unordered_map<const InjectiveFunction*, Queue>*
        s_worker_queues;
};

inline bool InjectiveFunction::defined(Ob key) const {
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    return m_set.contains(key);
}

inline bool InjectiveFunction::inverse_defined(Ob key) const {
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    return m_inverse_set.contains(key);
}

inline Ob InjectiveFunction::raw_find(Ob key) const {
    POMAGMA_ASSERT_RANGE_(5, key, item_dim());
    return m_values[key];
}

inline Ob InjectiveFunction::find(Ob key) const {
    POMAGMA_ASSERT_RANGE_(5, key, item_dim());
    return m_values[key];
}

inline Ob InjectiveFunction::inverse_find(Ob val) const {
    POMAGMA_ASSERT_RANGE_(5, val, item_dim());
    return m_inverse[val];
}

inline void InjectiveFunction::raw_insert(Ob key, Ob val) {
    POMAGMA_ASSERT5(val, "tried to set val to zero at " << key);
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    m_values[key] = val;
    m_set(key).one();

    m_inverse[val] = key;
    m_inverse_set(val).one();
}

inline void InjectiveFunction::insert(Ob key, Ob val) {
    POMAGMA_ASSERT5(val, "tried to set val to zero at " << key);
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    if (m_carrier.set_or_merge(m_values[key], val)) {
        m_set(key).one();
    }

    if (m_carrier.set_or_merge(m_inverse[val], key)) {
        m_inverse_set(val).one();
    }
}

inline void InjectiveFunction::lazy_insert(Ob key, Ob val) const {
    worker_queue().insert(key, val);
}

inline InjectiveFunction::Queue& InjectiveFunction::worker_queue() const {
    if (unlikely(s_worker_queues == nullptr)) {
        // never freed
        s_worker_queues =
            new std::unordered_map<const InjectiveFunction*, Queue>;
    }
    return (*s_worker_queues)[this];
}

}  // namespace pomagma
