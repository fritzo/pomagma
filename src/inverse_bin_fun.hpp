#ifndef POMAGMA_INVERSE_BIN_FUN_HPP
#define POMAGMA_INVERSE_BIN_FUN_HPP

#include "util.hpp"
#include "binary_function.hpp"
#include <vector>
#include <utility>
#include <tbb/concurrent_unordered_map.h>
#include <tbb/concurrent_unordered_set.h>

namespace pomagma
{

typedef std::vector<
    tbb::concurrent_unordered_set<std::pair<Ob, Ob>>> Vlr_Data;

typedef tbb::concurrent_unordered_map<
    std::pair<Ob, Ob>,
    tbb::concurrent_unordered_set<Ob>> VXx_Data;

inline bool contains (const Vlr_Data & Vlr_data, Ob V, Ob l, Ob r)
{
    auto & lr_set = Vlr_data[V];
    return lr_set.find(std::make_pair(l, r)) != lr_set.end();
}

inline bool contains (const VXx_Data & VXx_data, Ob V, Ob X, Ob x)
{
    auto i = VXx_data.find(std::make_pair(V, X));
    if (i == VXx_data.end()) {
        return false;
    }
    return i->second.find(x) != i->second.end();
}

inline void unsafe_erase (VXx_Data & VXx_data, Ob V, Ob X, Ob x)
{
    auto i = VXx_data.find(std::make_pair(V, X));
    POMAGMA_ASSERT1(i != VXx_data.end(),
            "double erase: " << V << "," << X << "," << x);
    i->second.unsafe_erase(x);
    if (i->second.empty()) {
        VXx_data.unsafe_erase(i);
    }
}

//----------------------------------------------------------------------------
// Inverse binary function

class inverse_bin_fun : noncopyable
{
    const DenseSet m_support;

    Vlr_Data m_Vlr_data;
    VXx_Data m_VLr_data;
    VXx_Data m_VRl_data;

public:

    inverse_bin_fun (const Carrier & carrier)
        : m_support(carrier.support(), yes_copy_construct),
          m_Vlr_data(item_dim()),
          m_VLr_data(),
          m_VRl_data()
    {
    }

    const DenseSet & support () const { return m_support; }
    size_t item_dim () const { return support().item_dim(); }

    void insert (Ob lhs, Ob rhs, Ob val);
    void unsafe_remove (Ob lhs, Ob rhs, Ob val);
    void validate (BinaryFunction & fun);

    class Vlr_Iterator;

    enum { LHS_FIXED = false, RHS_FIXED = true };
    template<bool idx> class VXx_Iterator;
};

inline void inverse_bin_fun::insert (Ob lhs, Ob rhs, Ob val)
{
    m_Vlr_data[val].insert(std::make_pair(lhs, rhs));
    m_VLr_data[std::make_pair(val, lhs)].insert(rhs);
    m_VRl_data[std::make_pair(val, rhs)].insert(lhs);
}

inline void inverse_bin_fun::unsafe_remove (Ob lhs, Ob rhs, Ob val)
{
    m_Vlr_data[val].unsafe_erase(std::make_pair(lhs, rhs));
    unsafe_erase(m_VLr_data, val, lhs, rhs);
    unsafe_erase(m_VRl_data, val, rhs, lhs);
}

//----------------------------------------------------------------------------
// Iteration

class inverse_bin_fun::Vlr_Iterator : noncopyable
{
    inverse_bin_fun & m_fun;
    tbb::concurrent_unordered_set<std::pair<Ob, Ob>>::iterator m_iter;
    tbb::concurrent_unordered_set<std::pair<Ob, Ob>>::iterator m_end;
    Ob m_val;

public:

    // construction
    Vlr_Iterator (inverse_bin_fun & fun)
        : m_fun(fun),
          m_val(0)
          // XXX FIXME is it ok to default-construct m_iter, m_end?
    {
    }
    Vlr_Iterator (inverse_bin_fun & fun, Ob val)
        : m_fun(fun),
          m_val(val)
    {
        begin();
    }

    // traversal
    void begin ()
    {
        auto i = m_fun.m_Vlr_data[m_val];
        m_iter = i.begin();
        m_end = i.end();
    }
    void begin (Ob val) { m_val = val; begin(); }
    bool ok () const { return m_iter != m_end; }
    void next () { ++m_iter; }

    // dereferencing
    Ob value () const { POMAGMA_ASSERT_OK return m_val; }
    Ob lhs () const { POMAGMA_ASSERT_OK return m_iter->first; }
    Ob rhs () const { POMAGMA_ASSERT_OK return m_iter->second; }
};

//----------------------------------------------------------------------------
// Range iteration

template<bool idx>
class inverse_bin_fun::VXx_Iterator : noncopyable
{
    inverse_bin_fun & m_fun;
    tbb::concurrent_unordered_set<Ob>::iterator m_iter;
    tbb::concurrent_unordered_set<Ob>::iterator m_end;
    std::pair<Ob, Ob> m_pair;

public:

    // construction
    VXx_Iterator (inverse_bin_fun & fun)
        : m_fun(fun),
          m_pair(0,0)
    {
    }
    VXx_Iterator (inverse_bin_fun & fun, Ob val, Ob fixed)
        : m_fun(fun),
          m_pair(val, fixed)
    {
        begin();
    }

    // traversal
    void begin ()
    {
        auto & map = idx ? m_fun.m_VRl_data : m_fun.m_VLr_data;
        auto i = map.find(m_pair);
        if (i != map.end()) {
            m_iter = i->second.begin();
            m_end = i->second.end();
        } else {
            m_iter = m_end;
        }
    }
    void begin (Ob val, Ob fixed)
    {
        m_pair = std::make_pair(val, fixed);
        begin();
    }
    bool ok () const { return m_iter != m_end; }
    void next  () { ++m_iter; }

    // dereferencing
    Ob value () const { POMAGMA_ASSERT_OK return m_pair.first; }
    Ob fixed () const { POMAGMA_ASSERT_OK return m_pair.second; }
    Ob moving () const { POMAGMA_ASSERT_OK return *m_iter; }
    Ob lhs () const { return idx ? moving() : fixed(); }
    Ob rhs () const { return idx ? fixed() : moving(); }
};

} // namespace pomagma

#endif // POMAGMA_INVERSE_BIN_FUN_HPP
