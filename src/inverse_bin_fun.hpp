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
    mutable Data m_data;

public:

    Vlr_Table (size_t size) : m_data(size)
    {
    }
    void move_from (const Vlr_Table & other)
    {
        size_t min_size = min(m_data.size(), other.m_data.size());
        for (size_t i = 1; i < min_size; ++i) {
            m_data[i] = other.m_data[i];
        }
    }

    bool contains (Ob lhs, Ob rhs, Ob val) const
    {
        const auto & lr_set = m_data[val];
        return lr_set.find(std::make_pair(lhs, rhs)) != lr_set.end();
    }
    void insert (Ob lhs, Ob rhs, Ob val) const
    {
        m_data[val].insert(std::make_pair(lhs, rhs));
    }

    Vlr_Table & unsafe_remove (Ob lhs, Ob rhs, Ob val)
    {
        m_data[val].unsafe_erase(std::make_pair(lhs, rhs));
        return * this;
    }
    Vlr_Table & unsafe_remove (Ob val)
    {
        m_data[val].clear();
        return * this;
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
template<bool transpose>
class VXx_Table : noncopyable
{
    typedef tbb::concurrent_unordered_set<Ob> Set;
    typedef tbb::concurrent_unordered_map<std::pair<Ob, Ob>, Set> Data;
    mutable Data m_data;

public:

    void move_from (const VXx_Table & other)
    {
        m_data = other.m_data;
    }

    bool contains (Ob lhs, Ob rhs, Ob val) const
    {
        Ob fixed = transpose ? rhs : lhs;
        Ob moving = transpose ? lhs : rhs;
        Data::const_iterator i = m_data.find(std::make_pair(val, fixed));
        if (i == m_data.end()) {
            return false;
        }
        return i->second.find(moving) != i->second.end();
    }
    void insert (Ob lhs, Ob rhs, Ob val) const
    {
        Ob fixed = transpose ? rhs : lhs;
        Ob moving = transpose ? lhs : rhs;
        m_data[std::make_pair(val, fixed)].insert(moving);
    }

    VXx_Table<transpose> & unsafe_remove (Ob lhs, Ob rhs, Ob val)
    {
        Ob fixed = transpose ? rhs : lhs;
        Ob moving = transpose ? lhs : rhs;
        Data::const_iterator i = m_data.find(std::make_pair(val, fixed));
        POMAGMA_ASSERT1(i != m_data.end(),
                "double erase: " << val << "," << lhs << "," << rhs);
        i->second.unsafe_erase(moving);
        if (i->second.empty()) {
            m_data.unsafe_erase(i);
        }
        return * this;
    }

    class Iterator
    {
        friend class VXx_Table<transpose>;

        const Data & m_data;
        Set::const_iterator m_iter;
        Set::const_iterator m_end;
        std::pair<Ob, Ob> m_pair;

        Iterator (const VXx_Table<transpose> * fun, Ob val, Ob fixed)
            : m_data(fun->m_data),
              m_pair(val, fixed)
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

    Iterator iter (Ob val, Ob fixed) const
    {
        return Iterator(this, val, fixed);
    }

    template<class Fun>
    void validate (const Fun * fun) const
    {
        for (const auto & val_fixed : m_data) {
            Ob val = val_fixed.first.first;
            Ob fixed = val_fixed.first.second;
            for (Ob moving : val_fixed.second) {
                Ob lhs = transpose ? moving : fixed;
                Ob rhs = transpose ? fixed : moving;
                POMAGMA_ASSERT_EQ(fun->find(lhs, rhs), val);
            }
        }
    }
};

typedef VXx_Table<0> VLr_Table;
typedef VXx_Table<1> VRl_Table;

} // namespace pomagma

#endif // POMAGMA_INVERSE_BIN_FUN_HPP
