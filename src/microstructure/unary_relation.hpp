#pragma once

#include "util.hpp"
#include "carrier.hpp"
#include <pomagma/platform/concurrent/dense_set.hpp>

namespace pomagma
{

class UnaryRelation : noncopyable
{
    const Carrier & m_carrier;
    mutable DenseSet m_set;
    void (*m_insert_callback) (const UnaryRelation *, Ob);

    mutable SharedMutex m_mutex;
    typedef SharedMutex::SharedLock SharedLock;
    typedef SharedMutex::UniqueLock UniqueLock;

public:

    UnaryRelation (
        const Carrier & carrier,
        void (*insert_callback) (const UnaryRelation *, Ob) = nullptr);
    ~UnaryRelation ();
    void validate () const;
    void validate_disjoint (const UnaryRelation & other) const;
    void log_stats (const std::string & prefix) const;
    size_t count_items () const { return m_set.count_items(); }

    // raw operations
    size_t item_dim () const { return m_carrier.item_dim(); }
    size_t word_dim () const { return m_set.word_dim(); }
    void raw_insert (Ob i) { m_set.insert(i); }
    void clear ();

    // relaxed operations
    const DenseSet & get_set () const { return m_set; }
    bool find (Ob i) const { return m_set.contains(i); }
    DenseSet::Iterator iter () const { return m_set.iter(); }
    void insert (Ob i);

    // strict operations
    void unsafe_merge (Ob dep);

private:

    const DenseSet & support () const { return m_carrier.support(); }
    bool supports (Ob i) const { return support().contains(i); }

    void _remove (Ob i) { m_set.remove(i); }
};

inline void UnaryRelation::insert (Ob i)
{
    if (m_set.try_insert(i)) {
        m_insert_callback(this, i);
    }
}

} // namespace pomagma
