#include "binary_function.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

BinaryFunction::BinaryFunction (const Carrier & carrier)
    : m_lines(carrier),
      m_block_dim((item_dim() + ITEMS_PER_BLOCK) / ITEMS_PER_BLOCK),
      m_blocks(alloc_blocks<Block>(m_block_dim * m_block_dim)),
      m_Vlr_table(1 + item_dim())
{
    POMAGMA_DEBUG("creating BinaryFunction with "
            << (m_block_dim * m_block_dim) << " blocks");

    std::atomic<Ob> * obs = & m_blocks[0][0];
    size_t ob_dim = m_block_dim * ITEMS_PER_BLOCK;
    construct_blocks(obs, ob_dim * ob_dim, 0);
}

BinaryFunction::~BinaryFunction ()
{
    std::atomic<Ob> * obs = &m_blocks[0][0];
    size_t ob_dim = m_block_dim * ITEMS_PER_BLOCK;
    destroy_blocks(obs, ob_dim * ob_dim);
    free_blocks(m_blocks);
}

void BinaryFunction::move_from (const BinaryFunction & other)
{
    POMAGMA_DEBUG("Copying BinaryFunction");

    size_t min_block_dim = min(m_block_dim, other.m_block_dim);
    for (size_t j_ = 0; j_ < min_block_dim; ++j_) {
        std::atomic<Ob> * destin = _block(0, j_);
        const std::atomic<Ob> * source = other._block(0, j_);
        memcpy(destin, source, sizeof(Block) * min_block_dim); // unsafe
    }

    m_lines.move_from(other.m_lines);
    m_Vlr_table.move_from(other.m_Vlr_table);
    m_VLr_table.move_from(other.m_VLr_table);
    m_VRl_table.move_from(other.m_VRl_table);
}

void BinaryFunction::validate () const
{
    SharedLock lock(m_mutex);

    POMAGMA_DEBUG("Validating BinaryFunction");

    m_lines.validate();

    POMAGMA_DEBUG("validating line-block consistency");
    for (size_t i_ = 0; i_ < m_block_dim; ++i_)
    for (size_t j_ = 0; j_ < m_block_dim; ++j_) {
        const std::atomic<Ob> * block = _block(i_, j_);

        for (size_t _i = 0; _i < ITEMS_PER_BLOCK; ++_i)
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
                POMAGMA_ASSERT(defined(i, j),
                        "found unsupported value: " << i << ',' << j);
            } else {
                POMAGMA_ASSERT(not defined(i, j),
                        "found supported null value: " << i << ',' << j);
            }
        }
    }

    POMAGMA_INFO("Validating inverse contains function");
    for (DenseSet::Iterator lhs_iter(support());
        lhs_iter.ok();
        lhs_iter.next())
    {
        Ob lhs = *lhs_iter;
        DenseSet rhs_set = get_Lx_set(lhs);
        for (DenseSet::Iterator rhs_iter(rhs_set);
            rhs_iter.ok();
            rhs_iter.next())
        {
            Ob rhs = *rhs_iter;
            Ob val = find(lhs, rhs);

            POMAGMA_ASSERT_CONTAINS3(m_Vlr_table, lhs, rhs, val);
            POMAGMA_ASSERT_CONTAINS3(m_VLr_table, lhs, rhs, val);
            POMAGMA_ASSERT_CONTAINS3(m_VRl_table, lhs, rhs, val);
        }
    }

    POMAGMA_INFO("Validating function contains inverse");
    m_Vlr_table.validate(this);
    m_VLr_table.validate(this);
    m_VRl_table.validate(this);
}

void BinaryFunction::insert (Ob lhs, Ob rhs, Ob val) const
{
    SharedLock lock(m_mutex);

    POMAGMA_ASSERT5(support().contains(lhs), "unsupported lhs: " << lhs);
    POMAGMA_ASSERT5(support().contains(rhs), "unsupported rhs: " << rhs);
    POMAGMA_ASSERT5(support().contains(val), "unsupported val: " << val);

    if (carrier().set_or_merge(value(lhs, rhs), val)) {
        m_lines.Lx(lhs, rhs).one();
        m_lines.Rx(lhs, rhs).one();
        m_Vlr_table.insert(lhs, rhs, val);
        m_VLr_table.insert(lhs, rhs, val);
        m_VRl_table.insert(lhs, rhs, val);
    }
}

void BinaryFunction::unsafe_remove (const Ob dep)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT5(support().contains(dep), "unsupported dep: " << dep);

    DenseSet set(item_dim(), NULL);

    {   Ob rhs = dep;
        set.init(m_lines.Rx(rhs));
        for (DenseSet::Iterator iter(set); iter.ok(); iter.next()) {
            Ob lhs = *iter;
            std::atomic<Ob> & atomic_val = value(lhs, rhs);
            Ob val = atomic_val.load(std::memory_order_relaxed);
            atomic_val.store(0, std::memory_order_relaxed);
            m_Vlr_table.unsafe_remove(lhs, rhs, val);
            m_VLr_table.unsafe_remove(lhs, rhs, val);
            m_VRl_table.unsafe_remove(lhs, rhs, val);
            m_lines.Lx(lhs, rhs).zero();
        }
        set.zero();
    }

    {   Ob lhs = dep;
        set.init(m_lines.Lx(lhs));
        for (DenseSet::Iterator iter(set); iter.ok(); iter.next()) {
            Ob rhs = *iter;
            std::atomic<Ob> & atomic_val = value(lhs, rhs);
            Ob val = atomic_val.load(std::memory_order_relaxed);
            atomic_val.store(0, std::memory_order_relaxed);
            m_Vlr_table.unsafe_remove(lhs, rhs, val);
            m_VLr_table.unsafe_remove(lhs, rhs, val);
            m_VRl_table.unsafe_remove(lhs, rhs, val);
            m_lines.Rx(lhs, rhs).zero();
        }
        set.zero();
    }

    {   Ob val = dep;
        for (auto iter = iter_val(val); iter.ok(); iter.next()) {
            Ob lhs = iter.lhs();
            Ob rhs = iter.rhs();
            std::atomic<Ob> & atomic_val = value(lhs, rhs);
            POMAGMA_ASSERT3(val == atomic_val.load(),
                    "double removal: " << lhs << ", " << rhs << ", " << val);
            atomic_val.store(0, std::memory_order_relaxed);
            m_lines.Lx(lhs, rhs).zero();
            m_lines.Rx(lhs, rhs).zero();
            m_VLr_table.unsafe_remove(lhs, rhs, val);
            m_VRl_table.unsafe_remove(lhs, rhs, val);
        }
        m_Vlr_table.unsafe_remove(val);
    }
}

void BinaryFunction::unsafe_merge (const Ob dep)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT5(support().contains(dep), "unsupported dep: " << dep);
    Ob rep = carrier().find(dep);
    POMAGMA_ASSERT5(support().contains(rep), "unsupported rep: " << rep);
    POMAGMA_ASSERT4(rep != dep, "self merge: " << dep << "," << rep);

    DenseSet dep_set(item_dim(), NULL);
    DenseSet rep_set(item_dim(), NULL);

    // Note: in some cases, triples may move multiple times, e.g.
    //   (dep, dep) --> (dep, rep) --> (rep, rep)

    // dep as rhs
    dep_set.init(m_lines.Rx(dep));
    for (DenseSet::Iterator iter(dep_set); iter.ok(); iter.next()) {
        Ob lhs = *iter;
        std::atomic<Ob> & dep_val = value(lhs, dep);
        std::atomic<Ob> & rep_val = value(lhs, rep);
        Ob val = dep_val.load(std::memory_order_relaxed);
        dep_val.store(0, std::memory_order_relaxed);
        m_lines.Lx(lhs, dep).zero();
        if (carrier().set_or_merge(rep_val, val)) {
            m_lines.Lx(lhs, rep).one();
            m_Vlr_table.unsafe_remove(lhs, dep, val).insert(lhs, rep, val);
            m_VLr_table.unsafe_remove(lhs, dep, val).insert(lhs, rep, val);
            m_VRl_table.unsafe_remove(lhs, dep, val).insert(lhs, rep, val);
        } else {
            m_Vlr_table.unsafe_remove(lhs, dep, val);
            m_VLr_table.unsafe_remove(lhs, dep, val);
            m_VRl_table.unsafe_remove(lhs, dep, val);
        }
    }
    rep_set.init(m_lines.Rx(rep));
    rep_set.merge(dep_set);

    // dep as lhs
    rep = carrier().find(rep);
    dep_set.init(m_lines.Lx(dep));
    for (DenseSet::Iterator iter(dep_set); iter.ok(); iter.next()) {
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
            m_VRl_table.unsafe_remove(dep, rhs, val).insert(rep, rhs, val);
        } else {
            m_Vlr_table.unsafe_remove(dep, rhs, val);
            m_VLr_table.unsafe_remove(dep, rhs, val);
            m_VRl_table.unsafe_remove(dep, rhs, val);
        }
    }
    rep_set.init(m_lines.Lx(rep));
    rep_set.merge(dep_set);

    // dep as val
    rep = carrier().find(rep);
    for (auto iter = iter_val(dep); iter.ok(); iter.next()) {
        Ob lhs = iter.lhs();
        Ob rhs = iter.rhs();
        value(lhs, rhs).store(rep, std::memory_order_relaxed);
        m_Vlr_table.insert(lhs, rhs, rep);
        m_VLr_table.unsafe_remove(lhs, rhs, dep).insert(lhs, rhs, rep);
        m_VRl_table.unsafe_remove(lhs, rhs, dep).insert(lhs, rhs, rep);
    }
    m_Vlr_table.unsafe_remove(dep);
}

} // namespace pomagma
