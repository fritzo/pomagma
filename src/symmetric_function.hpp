#ifndef POMAGMA_SYMMETRIC_FUNCTION_HPP
#define POMAGMA_SYMMETRIC_FUNCTION_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include "base_bin_rel.hpp"

namespace pomagma
{

// WARNING zero/null items are not allowed

inline size_t unordered_pair_count (size_t i) { return (i * (i + 1)) / 2; }

// a tight symmetric binary function in 4x4 word blocks
class SymmetricFunction : noncopyable
{
    base_sym_rel m_lines;
    const size_t m_block_dim;
    Block * const m_blocks;

    // block wrappers
    template<class T>
    static void sort (T & i, T & j) { if (j < i) { T k = j; j = i; i = k; }  }
    Ob * _block (int i_, int j_)
    {
        return m_blocks[unordered_pair_count(j_) + i_];
    }
    const Ob * _block (int i_, int j_) const
    {
        return m_blocks[unordered_pair_count(j_) + i_];
    }

public:

    // set wrappers
    DenseSet get_Lx_set (Ob lhs) const { return m_lines.Lx_set(lhs); }

    // ctors & dtors
    SymmetricFunction (const Carrier & carrier);
    ~SymmetricFunction ();
    void move_from (const SymmetricFunction & other); // for growing

    // function calling
private:
    inline Ob & value (Ob lhs, Ob rhs);
public:
    inline Ob value (Ob lhs, Ob rhs) const;
    Ob get_value (Ob lhs, Ob rhs) const { return value(lhs, rhs); }
    Ob find (Ob lhs, Ob rhs) const { return value(lhs, rhs); }

    // attributes
    size_t item_dim () const { return m_lines.item_dim(); }
private:
    const DenseSet & support () const { return m_lines.support(); }
public:
    size_t count_pairs () const; // slow!
    void validate () const;

    // element operations
    // TODO add a replace method for merging
    void insert (Ob lhs, Ob rhs, Ob val);
    void remove (Ob lhs, Ob rhs);
    bool contains (Ob lhs, Ob rhs) const
    {
        POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
        POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
        return m_lines.Lx(lhs, rhs);
    }

    // support operations
    void remove (
            const Ob i,
            void remove_value(Ob)); // rem
    void merge (
            const Ob i,
            const Ob j,
            void merge_values(Ob, Ob),     // dep, rep
            void move_value(Ob, Ob, Ob)); // moved, lhs, rhs

    // iteration
    class Iterator;
    class LLxx_Iter;
};

inline Ob & SymmetricFunction::value (Ob i, Ob j)
{
    sort(i, j);

    POMAGMA_ASSERT_RANGE_(5, i, item_dim());
    POMAGMA_ASSERT_RANGE_(5, j, item_dim());

    Ob * block = _block(i / ITEMS_PER_BLOCK, j / ITEMS_PER_BLOCK);
    return _block2value(block, i & BLOCK_POS_MASK, j & BLOCK_POS_MASK);
}

inline Ob SymmetricFunction::value (Ob i, Ob j) const
{
    sort(i, j);

    POMAGMA_ASSERT_RANGE_(5, i, item_dim());
    POMAGMA_ASSERT_RANGE_(5, j, item_dim());

    const Ob * block = _block(i / ITEMS_PER_BLOCK, j / ITEMS_PER_BLOCK);
    return _block2value(block, i & BLOCK_POS_MASK, j & BLOCK_POS_MASK);
}

inline void SymmetricFunction::insert (Ob lhs, Ob rhs, Ob val)
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    POMAGMA_ASSERT5(val, "tried to set val to zero at " << lhs << "," << rhs);

    Ob & old_val = value(lhs, rhs);
    POMAGMA_ASSERT2(not old_val, "double insertion: " << lhs << "," << rhs);
    old_val = val;

    bool_ref Lx_bit = m_lines.Lx(lhs, rhs);
    POMAGMA_ASSERT4(not Lx_bit, "double insertion: " << lhs << "," << rhs);
    Lx_bit.one();

    if (lhs == rhs) return;

    bool_ref Rx_bit = m_lines.Lx(rhs, lhs);
    POMAGMA_ASSERT4(not Rx_bit, "double insertion: " << lhs << "," << rhs);
    Rx_bit.one();
}

inline void SymmetricFunction::remove (Ob lhs, Ob rhs)
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);

    Ob & old_val = value(lhs, rhs);
    POMAGMA_ASSERT2(old_val, "double removal: " << lhs << "," << rhs);
    old_val = 0;

    bool_ref Lx_bit = m_lines.Lx(lhs, rhs);
    POMAGMA_ASSERT4(Lx_bit, "double removal: " << lhs << "," << rhs);
    Lx_bit.zero();

    if (lhs == rhs) return;

    bool_ref Rx_bit = m_lines.Lx(rhs, lhs);
    POMAGMA_ASSERT4(Rx_bit, "double removal: " << lhs << "," << rhs);
    Rx_bit.zero();
}

//----------------------------------------------------------------------------
// Iteration over a line

class SymmetricFunction::Iterator : noncopyable
{
    DenseSet m_set;
    DenseSet::Iter m_iter;
    const SymmetricFunction * m_fun;
    Ob m_fixed;
    Ob m_moving;

public:

    // construction
    Iterator (const SymmetricFunction * fun)
        : m_set(fun->item_dim(), NULL),
          m_iter(m_set, false),
          m_fun(fun),
          m_fixed(0),
          m_moving(0)
    {}
    Iterator (const SymmetricFunction * fun, Ob fixed)
        : m_set(fun->item_dim(), fun->m_lines.Lx(fixed)),
          m_iter(m_set, false),
          m_fun(fun),
          m_fixed(fixed),
          m_moving(0)
    {
        begin();
    }

    // traversal
private:
    void _set_pos () { m_moving = *m_iter; }
public:
    bool ok () const { return m_iter.ok(); }
    void begin () { m_iter.begin(); if (ok()) _set_pos(); }
    void begin (Ob fixed)
    {
        m_fixed=fixed;
        m_set.init(m_fun->m_lines.Lx(fixed));
        begin();
    }
    void next () { m_iter.next(); if (ok()) _set_pos(); }

    // dereferencing
private:
    void _deref_assert () const
    {
        POMAGMA_ASSERT5(ok(), "dereferenced done DenseSet::iter");
    }
public:
    Ob fixed () const { _deref_assert(); return m_fixed; }
    Ob moving () const { _deref_assert(); return m_moving; }
    Ob value () const
    {
        _deref_assert();
        return m_fun->get_value(m_fixed,m_moving);
    }
};

//------------------------------------------------------------------------
// Intersection iteration over 2 lines

class SymmetricFunction::LLxx_Iter : noncopyable
{
    DenseSet m_set;
    DenseSet::Iter m_iter;
    const SymmetricFunction * m_fun;
    Ob m_fixed1;
    Ob m_fixed2;
    Ob m_moving;

public:

    // construction
    LLxx_Iter (const SymmetricFunction* fun)
        : m_set(fun->item_dim()),
          m_iter(m_set, false),
          m_fun(fun)
    {
    }

    // traversal
    void begin () { m_iter.begin(); if (ok()) m_moving = *m_iter; }
    void begin (Ob fixed1, Ob fixed2)
    {
        DenseSet set1 = m_fun->get_Lx_set(fixed1);
        DenseSet set2 = m_fun->get_Lx_set(fixed2);
        m_set.set_insn(set1, set2);
        m_iter.begin();
        if (ok()) {
            m_fixed1 = fixed1;
            m_fixed2 = fixed2;
            m_moving = *m_iter;
        }
    }
    bool ok () const { return m_iter.ok(); }
    void next () { m_iter.next(); if (ok()) m_moving = *m_iter; }

    // dereferencing
    Ob fixed1 () const { return m_fixed1; }
    Ob fixed2 () const { return m_fixed2; }
    Ob moving () const { return m_moving; }
    Ob value1 () const { return m_fun->get_value(m_fixed1, m_moving); }
    Ob value2 () const { return m_fun->get_value(m_fixed2, m_moving); }
};

} // namespace pomagma

#endif // POMAGMA_SYMMETRIC_FUNCTION_HPP
