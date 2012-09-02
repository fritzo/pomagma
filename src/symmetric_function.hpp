#ifndef POMAGMA_SYMMETRIC_FUNCTION_HPP
#define POMAGMA_SYMMETRIC_FUNCTION_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include "base_bin_rel.hpp"

namespace pomagma
{

inline size_t unordered_pair_count (size_t i) { return (i * (i + 1)) / 2; }

// a tight symmetric binary function tiled in blocks
class SymmetricFunction : noncopyable
{
    mutable base_sym_rel m_lines;
    const size_t m_block_dim;
    Block * const m_blocks;

    mutable AssertSharedMutex m_mutex;
    typedef AssertSharedMutex::SharedLock SharedLock;
    typedef AssertSharedMutex::UniqueLock UniqueLock;

public:

    SymmetricFunction (const Carrier & carrier);
    ~SymmetricFunction ();
    void move_from (const SymmetricFunction & other); // for growing
    void validate () const;

    // safe operations
    DenseSet get_Lx_set (Ob lhs) const { return m_lines.Lx_set(lhs); }
    bool defined (Ob lhs, Ob rhs) const;
    Ob find (Ob lhs, Ob rhs) const { return value(lhs, rhs); }
    void insert (Ob lhs, Ob rhs, Ob val) const;

    // unsafe operations
    void remove (const Ob i);
    void merge (const Ob i, const Ob j);

private:

    const Carrier & carrier () const { return m_lines.carrier(); }
    const DenseSet & support () const { return m_lines.support(); }
    size_t item_dim () const { return m_lines.item_dim(); }

    template<class T>
    static void sort (T & i, T & j) { if (j < i) { T k = j; j = i; i = k; }  }

    std::atomic<Ob> & value (Ob lhs, Ob rhs) const;
    std::atomic<Ob> * _block (int i_, int j_) const
    {
        return m_blocks[unordered_pair_count(j_) + i_];
    }
};

inline bool SymmetricFunction::defined (Ob lhs, Ob rhs) const
{
    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    return m_lines.Lx(lhs, rhs);
}

inline std::atomic<Ob> & SymmetricFunction::value (Ob i, Ob j) const
{
    sort(i, j);

    POMAGMA_ASSERT_RANGE_(5, i, item_dim());
    POMAGMA_ASSERT_RANGE_(5, j, item_dim());

    std::atomic<Ob> * block = _block(i / ITEMS_PER_BLOCK, j / ITEMS_PER_BLOCK);
    return _block2value(block, i & BLOCK_POS_MASK, j & BLOCK_POS_MASK);
}

inline void SymmetricFunction::insert (Ob lhs, Ob rhs, Ob val) const
{
    SharedLock lock(m_mutex);

    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    POMAGMA_ASSERT_RANGE_(5, val, item_dim());

    std::atomic<Ob> & old_val = value(lhs, rhs);
    if (carrier().set_and_merge(val, old_val) == 0) {
        m_lines.Lx(lhs, rhs).one();
        m_lines.Lx(rhs, lhs).one();
    }
}

} // namespace pomagma

#endif // POMAGMA_SYMMETRIC_FUNCTION_HPP
