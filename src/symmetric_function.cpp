
#include "symmetric_function.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

SymmetricFunction::SymmetricFunction (const Carrier & carrier)
    : m_lines(carrier),
      m_block_dim((item_dim() + ITEMS_PER_BLOCK) / ITEMS_PER_BLOCK),
      m_blocks(pomagma::alloc_blocks<Block>(
                  unordered_pair_count(m_block_dim)))
{
    POMAGMA_DEBUG("creating SymmetricFunction with "
            << unordered_pair_count(m_block_dim) << " blocks");

    std::atomic<Ob> * obs = &m_blocks[0][0];
    size_t block_count = unordered_pair_count(m_block_dim);
    construct_blocks(obs, block_count * ITEMS_PER_BLOCK * ITEMS_PER_BLOCK, 0);
}

SymmetricFunction::~SymmetricFunction ()
{
    std::atomic<Ob> * obs = &m_blocks[0][0];
    size_t block_count = unordered_pair_count(m_block_dim);
    destroy_blocks(obs, block_count * ITEMS_PER_BLOCK * ITEMS_PER_BLOCK);
    pomagma::free_blocks(m_blocks);
}

void SymmetricFunction::move_from (const SymmetricFunction & other)
{
    POMAGMA_DEBUG("Copying SymmetricFunction");

    size_t min_block_dim = min(m_block_dim, other.m_block_dim);
    for (size_t j_ = 0; j_ < min_block_dim; ++j_) {
        std::atomic<Ob> * destin = _block(0, j_);
        const std::atomic<Ob> * source = other._block(0, j_);
        memcpy(destin, source, sizeof(Block) * (1 + j_));
    }

    m_lines.move_from(other.m_lines);
}

void SymmetricFunction::validate () const
{
    SharedLock lock(m_mutex);

    POMAGMA_DEBUG("Validating SymmetricFunction");

    m_lines.validate();

    POMAGMA_DEBUG("validating line-block consistency");
    for (size_t i_ = 0; i_ < m_block_dim; ++i_) {
    for (size_t j_ = i_; j_ < m_block_dim; ++j_) {
        const std::atomic<Ob> * block = _block(i_, j_);

        for (size_t _i = 0; _i < ITEMS_PER_BLOCK; ++_i) {
        for (size_t _j = 0; _j < ITEMS_PER_BLOCK; ++_j) {
            size_t i = i_ * ITEMS_PER_BLOCK + _i;
            size_t j = j_ * ITEMS_PER_BLOCK + _j;
            if (i == 0 or item_dim() < i) continue;
            if (j < i or item_dim() < j) continue;
            Ob val = _block2value(block, _i, _j);

            if (not (support().contains(i) and support().contains(j))) {
                POMAGMA_ASSERT(not val,
                        "found unsupported val: " << i << ',' << j);
            } else if (val) {
                POMAGMA_ASSERT(defined(i, j),
                        "found unsupported value: " << i << ',' << j);
            } else {
                POMAGMA_ASSERT(not defined(i, j),
                        "found supported null value: " << i << ',' << j);
            }
        }}
    }}
}

void SymmetricFunction::remove (const Ob dep)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT_RANGE_(4, dep, item_dim());

    DenseSet set(item_dim(), NULL);

    DenseSet lhs_fixed = get_Lx_set(dep);
    for (DenseSet::Iterator iter(lhs_fixed); iter.ok(); iter.next()) {
        Ob rhs = *iter;
        value(rhs, dep) = 0;

        set.init(m_lines.Lx(rhs));
        set.remove(dep);
    }
    set.init(m_lines.Lx(dep));
    set.zero();
}

void SymmetricFunction::merge (const Ob dep, const Ob rep)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT4(rep != dep, "self merge: " << dep << "," << rep);
    POMAGMA_ASSERT_RANGE_(4, dep, item_dim());
    POMAGMA_ASSERT_RANGE_(4, rep, item_dim());

    DenseSet set(item_dim(), NULL);
    DenseSet dep_set(item_dim(), NULL);
    DenseSet rep_set(item_dim(), NULL);

    // (dep, dep) -> (dep, rep)
    if (defined(dep, dep)) {
        std::atomic<Ob> & dep_val = value(dep, dep);
        std::atomic<Ob> & rep_val = value(rep, rep);
        carrier().set_and_merge(dep_val, rep_val);
        dep_val = 0;

        set.init(m_lines.Lx(dep));
        set(dep).zero();
        set(rep).one();
    }

    // (dep, rhs) --> (rep, rep) for rhs != dep
    DenseSet lhs_fixed = get_Lx_set(dep);
    for (DenseSet::Iterator iter(lhs_fixed); iter.ok(); iter.next()) {
        Ob rhs = *iter;
        std::atomic<Ob> & dep_val = value(rhs, dep);
        std::atomic<Ob> & rep_val = value(rhs, rep);
        carrier().set_and_merge(dep_val, rep_val);
        dep_val = 0;

        set.init(m_lines.Rx(dep));
        set(dep).zero();
        set(rep).one();
    }
    rep_set.init(m_lines.Lx(rep));
    dep_set.init(m_lines.Lx(dep));
    rep_set.merge(dep_set);
}

} // namespace pomagma
