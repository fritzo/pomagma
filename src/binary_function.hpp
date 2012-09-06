#ifndef POMAGMA_BINARY_FUNCTION_HPP
#define POMAGMA_BINARY_FUNCTION_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include "base_bin_rel.hpp"
#include "inverse_bin_fun.hpp"

namespace pomagma
{

// a tight binary function tiled in blocks
class BinaryFunction : noncopyable
{
    mutable base_bin_rel m_lines;
    const size_t m_block_dim;
    Block * const m_blocks;
    mutable Vlr_Table m_Vlr_table;
    mutable VLr_Table m_VLr_table;
    mutable VLr_Table m_VRl_table;

    mutable AssertSharedMutex m_mutex;
    typedef AssertSharedMutex::SharedLock SharedLock;
    typedef AssertSharedMutex::UniqueLock UniqueLock;

public:

    BinaryFunction (const Carrier & carrier);
    ~BinaryFunction ();
    void move_from (const BinaryFunction & other);
    void validate () const;

    // relaxed operations
    DenseSet get_Lx_set (Ob lhs) const { return m_lines.Lx_set(lhs); }
    DenseSet get_Rx_set (Ob rhs) const { return m_lines.Rx_set(rhs); }
    bool defined (Ob lhs, Ob rhs) const;
    Ob find (Ob lhs, Ob rhs) const { return value(lhs, rhs); }
    void insert (Ob lhs, Ob rhs, Ob val) const;

    // strict operations
    void unsafe_remove (const Ob i);
    void unsafe_merge (const Ob i, const Ob j);

private:

    const Carrier & carrier () const { return m_lines.carrier(); }
    const DenseSet & support () const { return m_lines.support(); }
    size_t item_dim () const { return support().item_dim(); }

    std::atomic<Ob> & value (Ob lhs, Ob rhs) const;
    std::atomic<Ob> * _block (size_t i_, size_t j_) const;
};

inline bool BinaryFunction::defined (Ob lhs, Ob rhs) const
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    return m_lines.Lx(lhs, rhs);
}

inline std::atomic<Ob> * BinaryFunction::_block (size_t i_, size_t j_) const
{
    return m_blocks[m_block_dim * j_ + i_];
}

inline std::atomic<Ob> & BinaryFunction::value (Ob i, Ob j) const
{
    POMAGMA_ASSERT_RANGE_(5, i, item_dim());
    POMAGMA_ASSERT_RANGE_(5, j, item_dim());

    std::atomic<Ob> * block = _block(i / ITEMS_PER_BLOCK, j / ITEMS_PER_BLOCK);
    return _block2value(block, i & BLOCK_POS_MASK, j & BLOCK_POS_MASK);
}

} // namespace pomagma

#endif // POMAGMA_BINARY_FUNCTION_HPP
