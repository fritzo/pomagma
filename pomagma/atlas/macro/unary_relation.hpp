#pragma once

#include <pomagma/util/sequential/dense_set.hpp>

#include "carrier.hpp"
#include "util.hpp"

namespace pomagma {

class UnaryRelation : noncopyable {
    const Carrier& m_carrier;
    mutable DenseSet m_set;

   public:
    explicit UnaryRelation(const Carrier& carrier);
    UnaryRelation(const Carrier& carrier, UnaryRelation&& other);
    ~UnaryRelation();
    void validate() const;
    void validate_disjoint(const UnaryRelation& other) const;
    void log_stats(const std::string& prefix) const;

    // raw operations
    size_t count_items() const { return m_set.count_items(); }
    size_t item_dim() const { return support().item_dim(); }
    size_t word_dim() const { return support().word_dim(); }
    DenseSet& raw_set() { return m_set; }
    void raw_insert(Ob i) const { m_set.raw_insert(i); }
    void update() {}
    void clear() { m_set.zero(); }

    // safe operations
    const DenseSet& get_set() const { return m_set; }
    bool find(Ob i) const { return m_set.contains(i); }
    DenseSet::Iterator iter() const { return m_set.iter(); }
    void insert(Ob i) { m_set.raw_insert(i); }

    // safe thread-locally queued operations
    void lazy_insert(Ob i) const;
    void lazy_gather() const;  // called by worker threads
    size_t lazy_flush();       // called by main thread

    // unsafe operations
    void unsafe_merge(Ob dep);

   private:
    const DenseSet& support() const { return m_carrier.support(); }
    bool supports(Ob i) const { return support().contains(i); }

    struct Queue {
        std::vector<Ob> m_tasks;
        void insert(Ob i) { m_tasks.push_back(i); }
        void clear() { std::vector<Ob>().swap(m_tasks); }
        void process_mergers(const Carrier& carrier);
    };
    Queue& worker_consequents() const;
    mutable Queue m_consequents;
    mutable std::mutex m_consequents_mutex;
    static thread_local std::unordered_map<const UnaryRelation*, Queue>*
        s_consequents;

    void _remove(Ob i) { m_set.remove(i); }
};

inline void UnaryRelation::lazy_insert(Ob i) const {
    worker_consequents().insert(i);
}

inline UnaryRelation::Queue& UnaryRelation::worker_consequents() const {
    if (unlikely(s_consequents == nullptr)) {
        // never freed
        s_consequents = new std::unordered_map<const UnaryRelation*, Queue>;
    }
    return (*s_consequents)[this];
}

}  // namespace pomagma
