#include "binary_function.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

BinaryFunction::BinaryFunction (const Carrier & carrier)
    : m_lines(carrier),
      m_block_dim((item_dim() + ITEMS_PER_BLOCK) / ITEMS_PER_BLOCK),
      m_blocks(pomagma::alloc_blocks<Block>(m_block_dim * m_block_dim))
{
    POMAGMA_DEBUG("creating BinaryFunction with "
            << (m_block_dim * m_block_dim) << " blocks");

    bzero(m_blocks, m_block_dim * m_block_dim * sizeof(Block));
}

BinaryFunction::~BinaryFunction ()
{
    pomagma::free_blocks(m_blocks);
}

// for growing
void BinaryFunction::move_from (const BinaryFunction & other)
{
    POMAGMA_DEBUG("Copying BinaryFunction");

    size_t min_block_dim = min(m_block_dim, other.m_block_dim);
    for (size_t j_ = 0; j_ < min_block_dim; ++j_) {
        Ob * destin = _block(0, j_);
        const Ob * source = other._block(0, j_);
        memcpy(destin, source, sizeof(Block) * min_block_dim);
    }

    m_lines.move_from(other.m_lines);
}

//----------------------------------------------------------------------------
// Diagnostics

size_t BinaryFunction::count_pairs () const
{
    DenseSet Lx_set(item_dim(), NULL);
    size_t result = 0;
    for (size_t i = 1; i <= item_dim(); ++i) {
        Lx_set.init(m_lines.Lx(i));
        result += Lx_set.count_items();
    }
    return result;
}

void BinaryFunction::validate () const
{
    POMAGMA_DEBUG("Validating BinaryFunction");

    m_lines.validate();

    POMAGMA_DEBUG("validating line-block consistency");
    for (size_t i_ = 0; i_ < m_block_dim; ++i_) {
    for (size_t j_ = 0; j_ < m_block_dim; ++j_) {
        const Ob * block = _block(i_,j_);

        for (size_t _i = 0; _i < ITEMS_PER_BLOCK; ++_i) {
        for (size_t _j = 0; _j < ITEMS_PER_BLOCK; ++_j) {
            size_t i = i_ * ITEMS_PER_BLOCK + _i;
            size_t j = j_ * ITEMS_PER_BLOCK + _j;
            if (i == 0 or item_dim() < i) continue;
            if (j == 0 or item_dim() < j) continue;
            Ob val = _block2value(block, _i, _j);

            if (not (support().contains(i) and support().contains(j))) {
                POMAGMA_ASSERT(not val,
                        "found unsupported val: " << i << ',' << j);
            } else if (val) {
                POMAGMA_ASSERT(contains(i, j),
                        "found unsupported value: " << i << ',' << j);
            } else {
                POMAGMA_ASSERT(not contains(i, j),
                        "found supported null value: " << i << ',' << j);
            }
        }}
    }}
}

//----------------------------------------------------------------------------
// Operations

void BinaryFunction::remove(
        const Ob dep,
        void remove_value(Ob)) // rem
{
    POMAGMA_ASSERT_RANGE_(4, dep, item_dim());

    DenseSet set(item_dim(), NULL);

    // (lhs, dep)
    DenseSet rhs_fixed = get_Rx_set(dep);
    for (DenseSet::Iter iter(rhs_fixed); iter.ok(); iter.next()) {
        Ob lhs = *iter;
        Ob & dep_val = value(lhs, dep);
        remove_value(dep_val);
        set.init(m_lines.Lx(lhs));
        set.remove(dep);
        dep_val = 0;
    }
    set.init(m_lines.Rx(dep));
    set.zero();

    // (dep, rhs)
    DenseSet lhs_fixed = get_Lx_set(dep);
    for (DenseSet::Iter iter(lhs_fixed); iter.ok(); iter.next()) {
        Ob rhs = *iter;
        Ob & dep_val = value(dep, rhs);
        remove_value(dep_val);
        set.init(m_lines.Rx(rhs));
        set.remove(dep);
        dep_val = 0;
    }
    set.init(m_lines.Lx(dep));
    set.zero();
}

void BinaryFunction::merge(
        const Ob dep,
        const Ob rep,
        void merge_values(Ob, Ob), // dep, rep
        void move_value(Ob, Ob, Ob)) // moved, lhs, rhs
{
    POMAGMA_ASSERT4(rep != dep, "self merge: " << dep << "," << rep);
    POMAGMA_ASSERT_RANGE_(4, dep, item_dim());
    POMAGMA_ASSERT_RANGE_(4, rep, item_dim());

    DenseSet set(item_dim(), NULL);
    DenseSet dep_set(item_dim(), NULL);
    DenseSet rep_set(item_dim(), NULL);

    // Note: the spacial case
    //   (dep, dep) --> (dep, rep) --> (rep, rep)
    // merges in two steps

    // (lhs, dep) --> (lhs, rep)
    DenseSet rhs_fixed = get_Rx_set(dep);
    for (DenseSet::Iter iter(rhs_fixed); iter.ok(); iter.next()) {
        Ob lhs = *iter;
        Ob & dep_val = value(lhs,dep);
        Ob & rep_val = value(lhs,rep);
        set.init(m_lines.Lx(lhs));
        set.remove(dep);
        if (rep_val) {
            merge_values(dep_val, rep_val);
        } else {
            move_value(dep_val, lhs, rep);
            set.insert(rep);
            rep_val = dep_val;
        }
        dep_val = 0;
    }
    rep_set.init(m_lines.Rx(rep));
    dep_set.init(m_lines.Rx(dep));
    rep_set.merge(dep_set);

    // (dep, rhs) --> (rep, rhs)
    DenseSet lhs_fixed = get_Lx_set(dep);
    for (DenseSet::Iter iter(lhs_fixed); iter.ok(); iter.next()) {
        Ob rhs = *iter;
        Ob & dep_val = value(dep, rhs);
        Ob & rep_val = value(rep, rhs);
        set.init(m_lines.Rx(rhs));
        set.remove(dep);
        if (rep_val) {
            merge_values(dep_val, rep_val);
        } else {
            move_value(dep_val, rep, rhs);
            set.insert(rep);
            rep_val = dep_val;
        }
        dep_val = 0;
    }
    rep_set.init(m_lines.Lx(rep));
    dep_set.init(m_lines.Lx(dep));
    rep_set.merge(dep_set);
}

} // namespace pomagma
