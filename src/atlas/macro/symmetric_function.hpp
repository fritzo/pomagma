#pragma once

#include "util.hpp"
#include "base_bin_rel.hpp"
#include <pomagma/util/sequential/dense_set.hpp>
#include <mutex>

namespace pomagma
{

// a tight symmetric binary function
class SymmetricFunction : noncopyable
{
    mutable base_sym_rel m_lines;
    mutable ObPairMap m_values;
    mutable std::mutex m_raw_mutex;

public:

    explicit SymmetricFunction (Carrier & carrier);
    SymmetricFunction (Carrier & carrier, SymmetricFunction && other);
    void validate () const;
    void log_stats (const std::string & prefix) const;

    // raw operations
    static bool is_symmetric () { return true; }
    size_t count_pairs () const { return m_values.size(); }
    void raw_lock () { m_raw_mutex.lock(); }
    void raw_insert (Ob lhs, Ob rhs, Ob val); // lock to concurrently write
    void raw_unlock () { m_raw_mutex.unlock(); }
    void update () {}
    void clear ();

    // safe operations
    // m_values is source of truth; m_lines lag
    DenseSet get_Lx_set (Ob lhs) const { return m_lines.Lx_set(lhs); }
    DenseSet get_Rx_set (Ob rhs) const { return m_lines.Rx_set(rhs); }
    bool defined (Ob lhs, Ob rhs) const;
    Ob find (Ob lhs, Ob rhs) const;
    Ob raw_find (Ob lhs, Ob rhs) const { return find(lhs, rhs); }
    DenseSet::Iterator iter_lhs (Ob lhs) const;
    DenseSet::Iterator iter_rhs (Ob rhs) const;
    void insert (Ob lhs, Ob rhs, Ob val) const;
    void update_values () const; // postcondition: all values are reps

    // unsafe operations
    void unsafe_merge (const Ob dep);

private:

    const Carrier & carrier () const { return m_lines.carrier(); }
    const DenseSet & support () const { return m_lines.support(); }
    size_t item_dim () const { return support().item_dim(); }

    template<class T>
    static void sort (T & i, T & j) { if (j < i) { T k = j; j = i; i = k; }  }

    static std::pair<Ob, Ob> make_sorted_pair (Ob i, Ob j)
    {
        sort(i, j);
        return std::make_pair(i, j);
    }

    static std::pair<Ob, Ob> assert_sorted_pair (Ob i, Ob j)
    {
        POMAGMA_ASSERT2(i <= j, "out of order pair: " << i << ", " << j);
        return std::make_pair(i, j);
    }
};

inline bool SymmetricFunction::defined (Ob lhs, Ob rhs) const
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    return m_lines.get_Lx(lhs, rhs);
}

inline Ob SymmetricFunction::find (Ob lhs, Ob rhs) const
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    auto i = m_values.find(make_sorted_pair(lhs, rhs));
    return i == m_values.end() ? 0 : i->second;
    //if (i == m_values.end()) {
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

inline DenseSet::Iterator SymmetricFunction::iter_lhs (Ob lhs) const
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    return DenseSet::Iterator(item_dim(), m_lines.Lx(lhs));
}

inline DenseSet::Iterator SymmetricFunction::iter_rhs (Ob rhs) const
{
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    return DenseSet::Iterator(item_dim(), m_lines.Rx(rhs));
}

inline void SymmetricFunction::raw_insert (Ob lhs, Ob rhs, Ob val)
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    m_values.insert(std::make_pair(assert_sorted_pair(lhs, rhs), val));
    m_lines.Lx(lhs, rhs).one();
    m_lines.Rx(lhs, rhs).one();
}

inline void SymmetricFunction::insert (Ob lhs, Ob rhs, Ob val) const
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    Ob & val_ref = m_values[make_sorted_pair(lhs, rhs)];
    if (val_ref) {
        carrier().set_and_merge(val_ref, val);
    } else {
        val_ref = val;
        m_lines.Lx(lhs, rhs).one();
        m_lines.Rx(lhs, rhs).one();
    }
}

} // namespace pomagma
