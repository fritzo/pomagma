#ifndef POMAGMA_INVERSE_BIN_FUN_HPP
#define POMAGMA_INVERSE_BIN_FUN_HPP

#include "util.hpp"
#include <vector>
#include <utility>
#include <tbb/concurrent_unordered_map.h>
#include <tbb/concurrent_unordered_set.h>

namespace pomagma
{

//----------------------------------------------------------------------------
// val -> lhs, rhs

class Vlr_Table
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

    class Iterator;
};

class Vlr_Table::Iterator : noncopyable
{
    const Vlr_Table::Data & m_data;
    Vlr_Table::Set::const_iterator m_iter;
    Vlr_Table::Set::const_iterator m_end;
    Ob m_val;

public:

    Iterator (const Vlr_Table & fun)
        : m_data(fun.m_data),
          m_val(0)
          // XXX FIXME is it ok to default-construct m_iter, m_end?
    {
    }
    Iterator (const Vlr_Table & fun, Ob val)
        : m_data(fun.m_data),
          m_val(val)
    {
        begin();
    }

    void begin ()
    {
        const Vlr_Table::Set & i = m_data[m_val];
        m_iter = i.begin();
        m_end = i.end();
    }
    void begin (Ob val) { m_val = val; begin(); }
    bool ok () const { return m_iter != m_end; }
    void next () { ++m_iter; }

    Ob lhs () const { POMAGMA_ASSERT_OK return m_iter->first; }
    Ob rhs () const { POMAGMA_ASSERT_OK return m_iter->second; }
};

//----------------------------------------------------------------------------
// val, lhs -> rhs

class VLr_Table
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

    class Iterator;
};

class VLr_Table::Iterator : noncopyable
{
    const VLr_Table::Data & m_data;
    VLr_Table::Set::const_iterator m_iter;
    VLr_Table::Set::const_iterator m_end;
    std::pair<Ob, Ob> m_pair;

public:

    Iterator (const VLr_Table & fun)
        : m_data(fun.m_data),
          m_pair(0, 0)
    {
    }
    Iterator (const VLr_Table & fun, Ob val, Ob lhs)
        : m_data(fun.m_data),
          m_pair(val, lhs)
    {
        begin();
    }

    void begin ()
    {
        VLr_Table::Data::const_iterator i = m_data.find(m_pair);
        if (i != m_data.end()) {
            m_iter = i->second.begin();
            m_end = i->second.end();
        } else {
            m_iter = m_end;
        }
    }
    void begin (Ob val, Ob lhs)
    {
        m_pair = std::make_pair(val, lhs);
        begin();
    }
    bool ok () const { return m_iter != m_end; }
    void next () { ++m_iter; }

    Ob operator * () const { POMAGMA_ASSERT_OK return *m_iter; }
};

} // namespace pomagma

#endif // POMAGMA_INVERSE_BIN_FUN_HPP
