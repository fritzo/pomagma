#ifndef POMAGMA_INVERSE_BIN_FUN_HPP
#define POMAGMA_INVERSE_BIN_FUN_HPP

#include "util.hpp"
#include <vector>
#include <utility>
#include <tbb/concurrent_unordered_map.h>
#include <tbb/concurrent_unordered_set.h>

namespace pomagma
{

// val -> lhs, rhs
class Vlr_Table : noncopyable
{
    typedef tbb::concurrent_unordered_set<std::pair<Ob, Ob>> Set;
    typedef std::vector<Set> Data;
    Data m_data;

public:

    Vlr_Table (size_t size) : m_data(size) {}

    bool contains (Ob lhs, Ob rhs, Ob val) const
    {
        const auto & lr_set = m_data[val];
        return lr_set.find(std::make_pair(lhs, rhs)) != lr_set.end();
    }
    void insert (Ob lhs, Ob rhs, Ob val)
    {
        m_data[val].insert(std::make_pair(lhs, rhs));
    }

    void unsafe_remove (Ob lhs, Ob rhs, Ob val)
    {
        m_data[val].unsafe_erase(std::make_pair(lhs, rhs));
    }
    void unsafe_remove (Ob val)
    {
        m_data[val].clear();
    }

    class Iterator
    {
        friend class Vlr_Table;

        const Data & m_data;
        Set::const_iterator m_iter;
        Set::const_iterator m_end;
        Ob m_val;

        Iterator (const Vlr_Table * fun, Ob val)
            : m_data(fun->m_data),
              m_val(val)
        {
            const Set & i = m_data[m_val];
            m_iter = i.begin();
            m_end = i.end();
        }

    public:

        bool ok () const { return m_iter != m_end; }
        void next () { ++m_iter; }

        Ob lhs () const { POMAGMA_ASSERT_OK return m_iter->first; }
        Ob rhs () const { POMAGMA_ASSERT_OK return m_iter->second; }
    };

    Iterator iter (Ob val) const { return Iterator(this, val); }

    template<class Fun>
    void validate (const Fun * fun) const
    {
        for (Ob val = 1, end = m_data.size(); val < end; ++val) {
            for (auto lhs_rhs : m_data[val]) {
                Ob lhs = lhs_rhs.first;
                Ob rhs = lhs_rhs.second;
                POMAGMA_ASSERT_EQ(fun->find(lhs, rhs), val);
            }
        }
    }
};

// val, lhs -> rhs
class VLr_Table : noncopyable
{
    typedef tbb::concurrent_unordered_set<Ob> Set;
    typedef tbb::concurrent_unordered_map<std::pair<Ob, Ob>, Set> Data;
    Data m_data;

public:

    bool contains (Ob lhs, Ob rhs, Ob val) const
    {
        Data::const_iterator i = m_data.find(std::make_pair(val, lhs));
        if (i == m_data.end()) {
            return false;
        }
        return i->second.find(rhs) != i->second.end();
    }
    void insert (Ob lhs, Ob rhs, Ob val)
    {
        m_data[std::make_pair(val, lhs)].insert(rhs);
    }

    void unsafe_remove (Ob lhs, Ob rhs, Ob val)
    {
        Data::const_iterator i = m_data.find(std::make_pair(val, lhs));
        POMAGMA_ASSERT1(i != m_data.end(),
                "double erase: " << val << "," << lhs << "," << rhs);
        i->second.unsafe_erase(rhs);
        if (i->second.empty()) {
            m_data.unsafe_erase(i);
        }
    }

    class Iterator
    {
        friend class VLr_Table;

        const Data & m_data;
        Set::const_iterator m_iter;
        Set::const_iterator m_end;
        std::pair<Ob, Ob> m_pair;

        Iterator (const VLr_Table * fun, Ob val, Ob lhs)
            : m_data(fun->m_data),
              m_pair(val, lhs)
        {
            Data::const_iterator i = m_data.find(m_pair);
            if (i != m_data.end()) {
                m_iter = i->second.begin();
                m_end = i->second.end();
            } else {
                POMAGMA_ASSERT6(
                    not (Set::const_iterator() != Set::const_iterator()),
                    "default constructed iterators do not equality compare");
                m_iter = m_end;
            }
        }

    public:

        bool ok () const { return m_iter != m_end; }
        void next () { ++m_iter; }

        Ob operator * () const { POMAGMA_ASSERT_OK return *m_iter; }
    };

    Iterator iter (Ob val, Ob lhs) const { return Iterator(this, val, lhs); }

    template<class Fun>
    void validate (const Fun * fun, bool transpose) const
    {
        for (const auto & val_lhs : m_data) {
            Ob val = val_lhs.first.first;
            Ob lhs = val_lhs.first.second;
            for (Ob rhs : val_lhs.second) {
                if (transpose) {
                    POMAGMA_ASSERT_EQ(fun->find(rhs, lhs), val);
                } else {
                    POMAGMA_ASSERT_EQ(fun->find(lhs, rhs), val);
                }
            }
        }
    }
};

} // namespace pomagma

#endif // POMAGMA_INVERSE_BIN_FUN_HPP
