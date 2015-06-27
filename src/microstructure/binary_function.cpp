#include "binary_function.hpp"
#include <pomagma/util/aligned_alloc.hpp>
#include <cstring>

namespace pomagma
{

static void noop_callback (const BinaryFunction *, Ob, Ob) {}

BinaryFunction::BinaryFunction (
        const Carrier & carrier,
        void (*insert_callback) (const BinaryFunction *, Ob, Ob))
    : m_lines(carrier),
      m_tile_dim((item_dim() + ITEMS_PER_TILE) / ITEMS_PER_TILE),
      m_tiles(alloc_blocks<Tile>(m_tile_dim * m_tile_dim)),
      m_Vlr_table(1 + item_dim()),
      m_insert_callback(insert_callback ? insert_callback : noop_callback)
{
    POMAGMA_DEBUG("creating BinaryFunction with "
            << (m_tile_dim * m_tile_dim) << " tiles");

    std::atomic<Ob> * obs = & m_tiles[0][0];
    size_t ob_dim = m_tile_dim * ITEMS_PER_TILE;
    construct_blocks(obs, ob_dim * ob_dim, 0);
}

BinaryFunction::~BinaryFunction ()
{
    std::atomic<Ob> * obs = &m_tiles[0][0];
    size_t ob_dim = m_tile_dim * ITEMS_PER_TILE;
    destroy_blocks(obs, ob_dim * ob_dim);
    free_blocks(m_tiles);
}

void BinaryFunction::validate () const
{
    SharedLock lock(m_mutex);

    POMAGMA_INFO("Validating BinaryFunction");

    m_lines.validate();

    POMAGMA_DEBUG("validating line-tile consistency");
    for (size_t i_ = 0; i_ < m_tile_dim; ++i_)
    for (size_t j_ = 0; j_ < m_tile_dim; ++j_) {
        const std::atomic<Ob> * tile = _tile(i_, j_);

        for (size_t _i = 0; _i < ITEMS_PER_TILE; ++_i)
        for (size_t _j = 0; _j < ITEMS_PER_TILE; ++_j) {
            size_t i = i_ * ITEMS_PER_TILE + _i;
            size_t j = j_ * ITEMS_PER_TILE + _j;
            if (i == 0 or item_dim() < i) continue;
            if (j == 0 or item_dim() < j) continue;
            Ob val = _tile2value(tile, _i, _j);

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

    POMAGMA_DEBUG("validating inverse contains function");
    for (auto lhs_iter = support().iter(); lhs_iter.ok(); lhs_iter.next()) {
        Ob lhs = *lhs_iter;
        for (auto rhs_iter = iter_lhs(lhs); rhs_iter.ok(); rhs_iter.next()) {
            Ob rhs = *rhs_iter;
            Ob val = find(lhs, rhs);

            POMAGMA_ASSERT_CONTAINS3(m_Vlr_table, lhs, rhs, val);
            POMAGMA_ASSERT_CONTAINS3(m_VLr_table, lhs, rhs, val);
            POMAGMA_ASSERT_CONTAINS3(m_VRl_table, lhs, rhs, val);
        }
    }

    POMAGMA_DEBUG("validating function contains inverse");
    m_Vlr_table.validate(this);
    m_VLr_table.validate(this);
    m_VRl_table.validate(this);
}

void BinaryFunction::log_stats (const std::string & prefix) const
{
    m_lines.log_stats(prefix);
}

void BinaryFunction::clear ()
{
    memory_barrier();
    m_lines.clear();
    zero_blocks(m_tiles, m_tile_dim * m_tile_dim);
    m_Vlr_table.clear();
    m_VLr_table.clear();
    m_VRl_table.clear();
    memory_barrier();
}

void BinaryFunction::unsafe_merge (const Ob dep)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT5(support().contains(dep), "unsupported dep: " << dep);
    Ob rep = carrier().find(dep);
    POMAGMA_ASSERT5(support().contains(rep), "unsupported rep: " << rep);
    POMAGMA_ASSERT4(rep != dep, "self merge: " << dep << "," << rep);

    // Note: in some cases, triples may move multiple times, e.g.
    //   (dep, dep) --> (dep, rep) --> (rep, rep)

    // dep as rhs
    for (auto iter = iter_rhs(dep); iter.ok(); iter.next()) {
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
    {
        DenseSet dep_set(item_dim(), m_lines.Rx(dep));
        DenseSet rep_set(item_dim(), m_lines.Rx(rep));
        rep_set.merge(dep_set);
    }

    // dep as lhs
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
            m_VRl_table.unsafe_remove(dep, rhs, val).insert(rep, rhs, val);
        } else {
            m_Vlr_table.unsafe_remove(dep, rhs, val);
            m_VLr_table.unsafe_remove(dep, rhs, val);
            m_VRl_table.unsafe_remove(dep, rhs, val);
        }
    }
    {
        DenseSet dep_set(item_dim(), m_lines.Lx(dep));
        DenseSet rep_set(item_dim(), m_lines.Lx(rep));
        rep_set.merge(dep_set);
    }

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
