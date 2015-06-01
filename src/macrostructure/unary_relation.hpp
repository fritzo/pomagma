#pragma once

#include "util.hpp"
#include "carrier.hpp"
#include <pomagma/platform/sequential/dense_set.hpp>

namespace pomagma
{

class UnaryRelation : noncopyable
{
    const Carrier & m_carrier;
    mutable DenseSet m_set;

public:

    UnaryRelation (const Carrier & carrier);
    UnaryRelation (const Carrier & carrier, UnaryRelation && other);
    ~UnaryRelation ();
    void validate () const;
    void validate_disjoint (const UnaryRelation & other) const;
    void log_stats (const std::string & prefix) const;

    // raw operations
    size_t count_items () const { return m_set.count_items(); }
    size_t item_dim () const { return support().item_dim(); }
    size_t word_dim () const { return support().word_dim(); }
    DenseSet & raw_set () { return m_set; }
    void raw_insert (Ob i) const { m_set.raw_insert(i); }
    void update () {}
    void clear () { m_set.zero(); }

    // safe operations
    const DenseSet & get_set () const { return m_set; }
    bool find (Ob i) const { return m_set.contains(i); }
    DenseSet::Iterator iter () const { return m_set.iter(); }
    void insert (Ob i) { m_set.raw_insert(i); }

    // unsafe operations
    void unsafe_merge (Ob dep);

private:

    const DenseSet & support () const { return m_carrier.support(); }
    bool supports (Ob i) const { return support().contains(i); }

    void _remove (Ob i) { m_set.remove(i); }
};

} // namespace pomagma
