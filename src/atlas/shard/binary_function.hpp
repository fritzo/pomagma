#pragma once

#include "util.hpp"
#include "carrier.hpp"
#include <unordered_map>

namespace pomagma {
namespace shard {

class BinaryFunction : noncopyable
{
    typedef std::unordered_map<Ob, Ob, TrivialObHash> Row;
    typedef std::unordered_map<Ob, Row, TrivialObHash> Table;
    typedef std::unordered_multimap<Ob, Ob, TrivialObHash> MultiRow;
    typedef std::unordered_map<Ob, MultiRow, TrivialObHash> MultiTable;
    Table m_lhs_rhs;
    Table m_rhs_lhs;
    MultiTable m_val_lhs;
    MultiTable m_val_rhs;
    Carrier & m_carrier;

public:

    BinaryFunction (Carrier & carrier);
    BinaryFunction (Carrier & carrier, BinaryFunction && other);
    void validate () const;
    void log_stats (const std::string & /* prefix */ ) const {}

    // raw operations
    static bool is_symmetric () { return false; }
    void raw_insert (Ob lhs, Ob rhs, Ob val);
    void clear ();

    class Iterator
    {
        Row::const_iterator m_pos;
        const Row::const_iterator m_end;
        static Row s_empty;

        Iterator () : m_pos(s_empty.begin()), m_end(s_empty.end()) {}
        explicit Iterator (const Row & row)
            : m_pos(row.begin()),
              m_end(row.end())
        {}

    public:

        bool ok () const { return m_pos != m_end; }
        void next () { ++m_pos; }
        Ob key () const { POMAGMA_ASSERT_OK return m_pos->first; }
        Ob val () const { POMAGMA_ASSERT_OK return m_pos->second; }

        friend class BinaryFunction;
    };

    // safe operations
    Ob find (Ob lhs, Ob rhs) const;
    Ob raw_find (Ob lhs, Ob rhs) const { return find(lhs, rhs); }
    Iterator iter_lhs (Ob lhs) const;
    Iterator iter_rhs (Ob rhs) const;
    void insert (Ob lhs, Ob rhs, Ob val);
    void merge (const Ob dep);

private:

    const Carrier & carrier () const { return m_carrier; }
    const DenseSet & support () const { return carrier().support(); }
    size_t item_dim () const { return support().item_dim(); }
};

inline Ob BinaryFunction::find (Ob lhs, Ob rhs) const
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    auto i = m_lhs_rhs.find(lhs);
    if (i != m_lhs_rhs.end()) {
        const Row & row = i->second;
        auto i = row.find(rhs);
        if (i != row.end()) {
            return i->second;
        }
    }
    return 0;
}

inline BinaryFunction::Iterator BinaryFunction::iter_lhs (Ob lhs) const
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    auto i = m_lhs_rhs.find(lhs);
    if (i == m_lhs_rhs.end()) {
        return Iterator();
    } else {
        return Iterator(i->second);
    }
}

inline BinaryFunction::Iterator BinaryFunction::iter_rhs (Ob rhs) const
{
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    auto i = m_rhs_lhs.find(rhs);
    if (i == m_rhs_lhs.end()) {
        return Iterator();
    } else {
        return Iterator(i->second);
    }
}

inline void BinaryFunction::raw_insert (Ob lhs, Ob rhs, Ob val)
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    m_lhs_rhs[lhs][rhs] = val;
    m_rhs_lhs[rhs][lhs] = val;
    m_val_lhs[val].insert(std::make_pair(lhs, rhs));
    m_val_rhs[val].insert(std::make_pair(rhs, lhs));
}

inline void BinaryFunction::insert (Ob lhs, Ob rhs, Ob val)
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    Ob & val_ref = m_lhs_rhs[lhs][rhs];
    if (val_ref) {
        carrier().set_and_merge(val_ref, val);
    } else {
        val_ref = val;
        m_rhs_lhs[rhs][lhs] = val;
        m_val_lhs[val].insert(std::make_pair(lhs, rhs));
        m_val_rhs[val].insert(std::make_pair(rhs, lhs));
    }
}

} // namespace shard
} // namespace pomagma
