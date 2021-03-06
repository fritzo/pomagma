#pragma once

#include "util.hpp"
#include <pomagma/util/concurrent/dense_set.hpp>
#include "carrier.hpp"

namespace pomagma {

class InjectiveFunction : noncopyable {
    const Carrier &m_carrier;
    mutable DenseSet m_set;
    mutable DenseSet m_inverse_set;
    std::atomic<Ob> *const m_values;
    std::atomic<Ob> *const m_inverse;
    void (*m_insert_callback)(const InjectiveFunction *, Ob);

    mutable AssertSharedMutex m_mutex;
    typedef AssertSharedMutex::SharedLock SharedLock;
    typedef AssertSharedMutex::UniqueLock UniqueLock;

   public:
    InjectiveFunction(const Carrier &carrier,
                      void (*insert_callback)(const InjectiveFunction *,
                                              Ob) = nullptr);
    ~InjectiveFunction();
    void validate() const;
    void log_stats(const std::string &prefix) const;

    // raw operations
    size_t count_items() const { return m_set.count_items(); }
    Ob raw_find(Ob key) const;
    void raw_insert(Ob key, Ob val);
    void update() {}
    void clear();

    // relaxed operations
    // m_values & m_inverse are source of truth; m_set & m_inverse_set lag
    const DenseSet &defined() const { return m_set; }
    const DenseSet &inverse_defined() const { return m_inverse_set; }
    bool defined(Ob key) const;
    bool inverse_defined(Ob key) const;
    Ob find(Ob key) const;
    Ob inverse_find(Ob val) const;
    DenseSet::Iterator iter() const { return m_set.iter(); }
    DenseSet::Iterator inverse_iter() const { return m_inverse_set.iter(); }
    void insert(Ob key, Ob val) const;

    // strict operations
    void unsafe_merge(Ob dep);

   private:
    const DenseSet &support() const { return m_carrier.support(); }
    size_t item_dim() const { return support().item_dim(); }
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
    return m_values[key].load(relaxed);
}

inline Ob InjectiveFunction::find(Ob key) const {
    POMAGMA_ASSERT_RANGE_(5, key, item_dim());
    return m_values[key].load(acquire);
}

inline Ob InjectiveFunction::inverse_find(Ob val) const {
    POMAGMA_ASSERT_RANGE_(5, val, item_dim());
    return m_inverse[val].load(acquire);
}

inline void InjectiveFunction::raw_insert(Ob key, Ob val) {
    POMAGMA_ASSERT5(val, "tried to set val to zero at " << key);
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    m_values[key].store(val, relaxed);
    m_set(key).one();

    m_inverse[val].store(key, relaxed);
    m_inverse_set(val).one();
}

inline void InjectiveFunction::insert(Ob key, Ob val) const {
    SharedLock lock(m_mutex);

    POMAGMA_ASSERT5(val, "tried to set val to zero at " << key);
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    if (m_carrier.set_and_merge(m_values[key], val)) {
        m_set(key).one();
        m_insert_callback(this, key);
    }

    if (m_carrier.set_and_merge(m_inverse[val], key)) {
        m_inverse_set(val).one();
    }
}

}  // namespace pomagma
