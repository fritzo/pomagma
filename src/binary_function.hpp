#ifndef POMAGMA_BINARY_FUNCTION_HPP
#define POMAGMA_BINARY_FUNCTION_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include "base_bin_rel.hpp"

namespace pomagma
{

// WARNING zero/null items are not allowed

// a tight binary function in 4x4 word blocks
class BinaryFunction : noncopyable
{
    base_bin_rel m_lines;
    const size_t m_block_dim;
    Block * const m_blocks;

    // block wrappers
    Ob * _block (size_t i_, size_t j_)
    {
        return m_blocks[m_block_dim * j_ + i_];
    }
    const Ob * _block (size_t i_, size_t j_) const
    {
        return m_blocks[m_block_dim * j_ + i_];
    }

public:

    // set wrappers
    DenseSet get_Lx_set (Ob lhs) const { return m_lines.Lx_set(lhs); }
    DenseSet get_Rx_set (Ob rhs) const { return m_lines.Rx_set(rhs); }

    // ctors & dtors
    BinaryFunction (const Carrier & carrier);
    ~BinaryFunction ();
    void move_from (const BinaryFunction & other); // for growing

    // function calling
private:
    inline Ob & value (Ob lhs, Ob rhs);
public:
    inline Ob value (Ob lhs, Ob rhs) const;
    Ob get_value (Ob lhs, Ob rhs) const { return value(lhs, rhs); }
    Ob find (Ob lhs, Ob rhs) const { return value(lhs, rhs); }

    // attributes
    size_t item_dim () const { return m_lines.item_dim(); }
    const DenseSet & support () const { return m_lines.support(); }
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
            void merge_values(Ob, Ob), // dep, rep
            void move_value(Ob, Ob, Ob)); // moved, lhs, rhs
};

inline Ob & BinaryFunction::value (Ob i, Ob j)
{
    POMAGMA_ASSERT_RANGE_(5, i, item_dim());
    POMAGMA_ASSERT_RANGE_(5, j, item_dim());

    Ob * block = _block(i / ITEMS_PER_BLOCK, j / ITEMS_PER_BLOCK);
    return _block2value(block, i & BLOCK_POS_MASK, j & BLOCK_POS_MASK);
}

inline Ob BinaryFunction::value (Ob i, Ob j) const
{
    POMAGMA_ASSERT_RANGE_(5, i, item_dim());
    POMAGMA_ASSERT_RANGE_(5, j, item_dim());

    const Ob * block = _block(i / ITEMS_PER_BLOCK, j / ITEMS_PER_BLOCK);
    return _block2value(block, i & BLOCK_POS_MASK, j & BLOCK_POS_MASK);
}

inline void BinaryFunction::insert (Ob lhs, Ob rhs, Ob val)
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

    bool_ref Rx_bit = m_lines.Rx(lhs, rhs);
    POMAGMA_ASSERT4(not Rx_bit, "double insertion: " << lhs << "," << rhs);
    Rx_bit.one();
}

inline void BinaryFunction::remove (Ob lhs, Ob rhs)
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);

    Ob & old_val = value(lhs, rhs);
    POMAGMA_ASSERT2(old_val, "double removal: " << lhs << "," << rhs);
    old_val = 0;

    bool_ref Lx_bit = m_lines.Lx(lhs, rhs);
    POMAGMA_ASSERT4(Lx_bit, "double removal: " << lhs << "," << rhs);
    Lx_bit.zero();

    bool_ref Rx_bit = m_lines.Rx(lhs, rhs);
    POMAGMA_ASSERT4(Rx_bit, "double removal: " << lhs << "," << rhs);
    Rx_bit.zero();
}

} // namespace pomagma

#endif // POMAGMA_BINARY_FUNCTION_HPP
