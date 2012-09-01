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
    Block4x4 * const m_blocks;

    // block wrappers
    oid_t * _block (size_t i_, size_t j_)
    {
        return m_blocks[m_block_dim * j_ + i_];
    }
    const oid_t * _block (size_t i_, size_t j_) const
    {
        return m_blocks[m_block_dim * j_ + i_];
    }

public:

    // set wrappers
    DenseSet get_Lx_set (oid_t lhs) const { return m_lines.Lx_set(lhs); }
    DenseSet get_Rx_set (oid_t rhs) const { return m_lines.Rx_set(rhs); }

    // ctors & dtors
    BinaryFunction (const Carrier & carrier);
    ~BinaryFunction ();
    void move_from (const BinaryFunction & other); // for growing

    // function calling
private:
    inline oid_t & value (oid_t lhs, oid_t rhs);
public:
    inline oid_t value (oid_t lhs, oid_t rhs) const;
    oid_t get_value (oid_t lhs, oid_t rhs) const { return value(lhs, rhs); }
    oid_t find (oid_t lhs, oid_t rhs) const { return value(lhs, rhs); }

    // attributes
    size_t item_dim () const { return m_lines.item_dim(); }
    const DenseSet & support () const { return m_lines.support(); }
    size_t count_pairs () const; // slow!
    void validate () const;

    // element operations
    // TODO add a replace method for merging
    void insert (oid_t lhs, oid_t rhs, oid_t val);
    void remove (oid_t lhs, oid_t rhs);
    bool contains (oid_t lhs, oid_t rhs) const
    {
        POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
        POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
        return m_lines.Lx(lhs, rhs);
    }

    // support operations
    void remove (
            const oid_t i,
            void remove_value(oid_t)); // rem
    void merge (
            const oid_t i,
            const oid_t j,
            void merge_values(oid_t, oid_t), // dep, rep
            void move_value(oid_t, oid_t, oid_t)); // moved, lhs, rhs
};

inline oid_t & BinaryFunction::value (oid_t i, oid_t j)
{
    POMAGMA_ASSERT_RANGE_(5, i, item_dim());
    POMAGMA_ASSERT_RANGE_(5, j, item_dim());

    oid_t * block = _block(i / ITEMS_PER_BLOCK, j / ITEMS_PER_BLOCK);
    return _block2value(block, i & BLOCK_POS_MASK, j & BLOCK_POS_MASK);
}

inline oid_t BinaryFunction::value (oid_t i, oid_t j) const
{
    POMAGMA_ASSERT_RANGE_(5, i, item_dim());
    POMAGMA_ASSERT_RANGE_(5, j, item_dim());

    const oid_t * block = _block(i / ITEMS_PER_BLOCK, j / ITEMS_PER_BLOCK);
    return _block2value(block, i & BLOCK_POS_MASK, j & BLOCK_POS_MASK);
}

inline void BinaryFunction::insert (oid_t lhs, oid_t rhs, oid_t val)
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    POMAGMA_ASSERT5(val, "tried to set val to zero at " << lhs << "," << rhs);

    oid_t & old_val = value(lhs, rhs);
    POMAGMA_ASSERT2(not old_val, "double insertion: " << lhs << "," << rhs);
    old_val = val;

    bool_ref Lx_bit = m_lines.Lx(lhs, rhs);
    POMAGMA_ASSERT4(not Lx_bit, "double insertion: " << lhs << "," << rhs);
    Lx_bit.one();

    bool_ref Rx_bit = m_lines.Rx(lhs, rhs);
    POMAGMA_ASSERT4(not Rx_bit, "double insertion: " << lhs << "," << rhs);
    Rx_bit.one();
}

inline void BinaryFunction::remove (oid_t lhs, oid_t rhs)
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);

    oid_t & old_val = value(lhs, rhs);
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
