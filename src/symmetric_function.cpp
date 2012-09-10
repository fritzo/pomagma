
#include "symmetric_function.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

SymmetricFunction::SymmetricFunction (const Carrier & carrier)
    : m_lines(carrier),
      m_block_dim((item_dim() + ITEMS_PER_BLOCK) / ITEMS_PER_BLOCK),
      m_blocks(pomagma::alloc_blocks<Block>(
                  unordered_pair_count(m_block_dim))),
      m_Vlr_table(1 + item_dim())
{
    POMAGMA_DEBUG("creating SymmetricFunction with "
            << unordered_pair_count(m_block_dim) << " blocks");

    std::atomic<Ob> * obs = & m_blocks[0][0];
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

void SymmetricFunction::copy_from (const SymmetricFunction & other)
{
    POMAGMA_DEBUG("Copying SymmetricFunction");

    size_t min_block_dim = min(m_block_dim, other.m_block_dim);
    for (size_t j_ = 0; j_ < min_block_dim; ++j_) {
        std::atomic<Ob> * destin = _block(0, j_);
        const std::atomic<Ob> * source = other._block(0, j_);
        memcpy(destin, source, sizeof(Block) * (1 + j_));
    }

    m_lines.copy_from(other.m_lines);
    m_Vlr_table.copy_from(other.m_Vlr_table);
    m_VLr_table.copy_from(other.m_VLr_table);
}

void SymmetricFunction::validate () const
{
    SharedLock lock(m_mutex);

    POMAGMA_DEBUG("Validating SymmetricFunction");

    m_lines.validate();

    POMAGMA_DEBUG("validating line-block consistency");
    for (size_t i_ = 0; i_ < m_block_dim; ++i_)
    for (size_t j_ = i_; j_ < m_block_dim; ++j_) {
        const std::atomic<Ob> * block = _block(i_, j_);

        for (size_t _i = 0; _i < ITEMS_PER_BLOCK; ++_i)
        for (size_t _j = 0; _j < ITEMS_PER_BLOCK; ++_j) {
            size_t i = i_ * ITEMS_PER_BLOCK + _i;
            size_t j = j_ * ITEMS_PER_BLOCK + _j;
            if (i == 0 or item_dim() < i) continue;
            if (j < i or item_dim() < j) continue;
            Ob val = _block2value(block, _i, _j);

            if (not (support().contains(i) and support().contains(j))) {
                POMAGMA_ASSERT(not val,
                    "found unsupported value " << i << ',' << j << ',' << val);
            } else if (val) {
                POMAGMA_ASSERT(defined(i, j),
                    "found undefined value " << i << ',' << j << ',' << val);
            } else {
                POMAGMA_ASSERT(not defined(i, j),
                        "found defined null value " << i << ',' << j);
            }
        }
    }

    POMAGMA_INFO("Validating inverse contains function");
    for (auto lhs_iter = support().iter(); lhs_iter.ok(); lhs_iter.next()) {
        Ob lhs = *lhs_iter;
        for (auto rhs_iter = iter_lhs(lhs); rhs_iter.ok(); rhs_iter.next()) {
            Ob rhs = *rhs_iter;
            Ob val = find(lhs, rhs);

            POMAGMA_ASSERT_CONTAINS3(m_Vlr_table, lhs, rhs, val);
            POMAGMA_ASSERT_CONTAINS3(m_VLr_table, lhs, rhs, val);
        }
    }

    POMAGMA_INFO("Validating function contains inverse");
    m_Vlr_table.validate(this);
    m_VLr_table.validate(this);
}

void SymmetricFunction::insert (Ob lhs, Ob rhs, Ob val) const
{
    SharedLock lock(m_mutex);

    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    if (carrier().set_or_merge(value(lhs, rhs), val)) {
        m_lines.Lx(lhs, rhs).one();
        m_lines.Rx(lhs, rhs).one();
        m_Vlr_table.insert(lhs, rhs, val);
        m_Vlr_table.insert(rhs, lhs, val);
        m_VLr_table.insert(lhs, rhs, val);
        m_VLr_table.insert(rhs, lhs, val);
    }
}

void SymmetricFunction::unsafe_remove (const Ob dep)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT5(support().contains(dep), "unsupported dep: " << dep);

    {   Ob lhs = dep;
        for (auto iter = iter_lhs(lhs); iter.ok(); iter.next()) {
            Ob rhs = *iter;
            std::atomic<Ob> & atomic_val = value(lhs, rhs);
            Ob val = atomic_val.load(std::memory_order_relaxed);
            POMAGMA_ASSERT3(val, "double removal: " << lhs << ", " << rhs);
            m_lines.Rx(lhs, rhs).zero();
            m_Vlr_table.unsafe_remove(lhs, rhs, val);
            m_VLr_table.unsafe_remove(lhs, rhs, val);
            if (lhs != rhs) {
                m_Vlr_table.unsafe_remove(rhs, lhs, val);
                m_VLr_table.unsafe_remove(rhs, lhs, val);
            }
            atomic_val.store(0, std::memory_order_relaxed);
        }
        DenseSet set(item_dim(), m_lines.Lx(lhs));
        set.zero();
    }

    {   Ob val = dep;
        for (auto iter = iter_val(val); iter.ok(); iter.next()) {
            Ob lhs = iter.lhs();
            Ob rhs = iter.rhs();
            m_lines.Lx(lhs, rhs).zero();
            m_VLr_table.unsafe_remove(lhs, rhs, val);
            if (lhs <= rhs) {
                POMAGMA_ASSERT3(value(lhs, rhs).load(),
                    "double removal: " << lhs << ", " << rhs);
                value(lhs, rhs).store(0, std::memory_order_relaxed);
            }
        }
        m_Vlr_table.unsafe_remove(val);
    }
}

void SymmetricFunction::unsafe_merge (const Ob dep)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT5(support().contains(dep), "unsupported dep: " << dep);
    Ob rep = carrier().find(dep);
    POMAGMA_ASSERT5(support().contains(rep), "unsupported rep: " << rep);
    POMAGMA_ASSERT4(rep != dep, "self merge: " << dep << "," << rep);

    // (dep, dep) -> (rep, rep)
    if (defined(dep, dep)) {
        std::atomic<Ob> & dep_val = value(dep, dep);
        std::atomic<Ob> & rep_val = value(rep, rep);
        Ob val = dep_val.load(std::memory_order_relaxed);
        dep_val.store(0, std::memory_order_relaxed);
        m_lines.Lx(dep, dep).zero();
        if (carrier().set_or_merge(rep_val, val)) {
            m_lines.Lx(rep, rep).one();
            m_Vlr_table.unsafe_remove(dep, dep, val).insert(rep, rep, val);
            m_VLr_table.unsafe_remove(dep, dep, val).insert(rep, rep, val);
        } else {
            m_Vlr_table.unsafe_remove(dep, dep, val);
            m_VLr_table.unsafe_remove(dep, dep, val);
        }
    }

    // (dep, rhs) --> (rep, rhs) for rhs != dep
    rep = carrier().find(rep);
    for (auto iter = iter_lhs(dep); iter.ok(); iter.next()) {
        Ob rhs = *iter;
        std::atomic<Ob> & dep_val = value(dep, rhs);
        std::atomic<Ob> & rep_val = value(rep, rhs);
        Ob val = dep_val.load(std::memory_order_relaxed);
        dep_val.store(0, std::memory_order_relaxed);
        m_lines.Rx(dep, rhs).zero();
        if (carrier().set_or_merge(rep_val, val)) {
            m_lines.Rx(rep, rhs).one();
            m_Vlr_table.unsafe_remove(dep, rhs, val).insert(rep, rhs, val);
            m_VLr_table.unsafe_remove(dep, rhs, val).insert(rep, rhs, val);
            m_Vlr_table.unsafe_remove(rhs, dep, val).insert(rhs, rep, val);
            m_VLr_table.unsafe_remove(rhs, dep, val).insert(rhs, rep, val);
        } else {
            m_Vlr_table.unsafe_remove(dep, rhs, val);
            m_VLr_table.unsafe_remove(dep, rhs, val);
            m_Vlr_table.unsafe_remove(rhs, dep, val);
            m_VLr_table.unsafe_remove(rhs, dep, val);
        }
    }
    DenseSet dep_set(item_dim(), m_lines.Lx(dep));
    DenseSet rep_set(item_dim(), m_lines.Lx(rep));
    rep_set.merge(dep_set);

    // dep as val
    rep = carrier().find(rep);
    for (auto iter = iter_val(dep); iter.ok(); iter.next()) {
        Ob lhs = iter.lhs();
        Ob rhs = iter.rhs();
        value(lhs, rhs).store(rep, std::memory_order_relaxed); // XXX error
        // XXX unsupported lhs = 50
        m_Vlr_table.insert(lhs, rhs, rep);
        m_VLr_table.unsafe_remove(lhs, rhs, dep).insert(lhs, rhs, rep);
    }
    m_Vlr_table.unsafe_remove(dep);
}

} // namespace pomagma
