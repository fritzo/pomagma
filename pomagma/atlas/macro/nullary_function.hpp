#pragma once

#include <pomagma/util/sequential/dense_set.hpp>

#include "carrier.hpp"
#include "util.hpp"

namespace pomagma {

class NullaryFunction : noncopyable {
    const Carrier& m_carrier;
    mutable Ob m_value;

   public:
    explicit NullaryFunction(const Carrier& carrier);
    NullaryFunction(const Carrier& carrier, NullaryFunction&& other);
    void validate() const;
    void log_stats(const std::string& prefix) const;

    // raw operations
    void raw_insert(Ob val);
    void update() {}
    void clear() { m_value = 0; }

    // safe operations
    bool defined() const { return m_value; }
    Ob find() const { return m_value; }
    void insert(Ob val) const;
    void update_values() const {}  // postcondition: all values are reps

    // safe thread-locally queued operations
    void lazy_insert(Ob val) const;
    void lazy_gather() const;
    size_t lazy_flush() const;

    // unsafe operations
    void unsafe_merge(Ob dep);

   private:
    struct Queue {
        std::vector<Ob> m_tasks;
        void insert(Ob val) { m_tasks.push_back(val); }
        void clear() { std::vector<Ob>().swap(m_tasks); }
        void process_mergers(const Carrier& carrier);
    };
    Queue& worker_consequents() const;
    mutable Queue m_consequents;
    mutable std::mutex m_consequents_mutex;
    static thread_local std::unordered_map<const NullaryFunction*, Queue>*
        s_consequents;

    const DenseSet& support() const { return m_carrier.support(); }
};

inline void NullaryFunction::raw_insert(Ob val) {
    POMAGMA_ASSERT5(val, "tried to set value to zero");
    POMAGMA_ASSERT5(support().contains(val), "unsupported value: " << val);

    m_value = val;
}

inline void NullaryFunction::insert(Ob val) const {
    POMAGMA_ASSERT5(val, "tried to set value to zero");
    POMAGMA_ASSERT5(support().contains(val), "unsupported value: " << val);

    m_carrier.set_or_merge(m_value, val);
}

inline void NullaryFunction::lazy_insert(Ob val) const {
    worker_consequents().insert(val);
}

inline NullaryFunction::Queue& NullaryFunction::worker_consequents() const {
    if (unlikely(s_consequents == nullptr)) {
        // never freed
        s_consequents = new std::unordered_map<const NullaryFunction*, Queue>;
    }
    return (*s_consequents)[this];
}

}  // namespace pomagma
