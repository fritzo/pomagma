#include <pomagma/analyst/intervals.hpp>
#include <functional>
#include <tuple>
#include <utility>
#include <vector>

namespace pomagma {
namespace intervals {

Approximator::Approximator (
        Structure & structure,
        DenseSetStore & sets,
        WorkerPool & worker_pool) :
    // structure
    m_structure(structure),
    m_item_dim(structure.carrier().item_dim()),
    m_top(structure.nullary_function("TOP").find()),
    m_bot(structure.nullary_function("BOT").find()),
    m_identity(structure.nullary_function("I").find()),
    m_less(structure.binary_relation("LESS")),
    m_nless(structure.binary_relation("NLESS")),
    m_join(structure.signature().symmetric_function("JOIN")),
    m_rand(structure.signature().symmetric_function("RAND")),
    m_quote(structure.signature().injective_function("QUOTE")),
    // dense set stores
    m_sets(sets),
    m_below(1 + m_item_dim),
    m_above(1 + m_item_dim),
    m_nbelow(1 + m_item_dim),
    m_nabove(1 + m_item_dim),
    m_union_cache(
        worker_pool,
        [m_item_dim, &m_sets](const std::pair<SetId, SetId> & pair){
            DenseSet val(m_item_dim);
            val.set_insn(m_sets.load(pair.first), m_sets.load(pair.second));
            return m_sets.store(std::move(val));
        })
{
    POMAGMA_ASSERT(m_top, "TOP is not defined");
    POMAGMA_ASSERT(m_bot, "BOT is not defined");
    POMAGMA_ASSERT(m_identity, "I is not defined");

    POMAGMA_INFO("Inserting LESS and NLESS in DenseSetStore");
    for (auto iter = m_structure.carrier().iter(); iter.ok(); iter.next()) {
        const Ob ob = * iter;
        m_known[BELOW][ob] = m_sets.store(m_less.get_Rx_set(ob));
        m_known[ABOVE][ob] = m_sets.store(m_less.get_Lx_set(ob));
        m_known[NBELOW][ob] = m_sets.store(m_nless.get_Rx_set(ob));
        m_known[NABOVE][ob] = m_sets.store(m_nless.get_Lx_set(ob));
    }

    POMAGMA_INFO("Initializing nullary_function cache");
    for (const auto & i : signature().nullary_functions()) {
        const uint64_t hash = hash_name(i.first);
        Ob ob = i.second->find();
        Approximation approx = ob ? known(ob) : unknown();
        for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
            m_nullary_cache.insert(
                {{hash, p, NULLARY_FUNCTION, VOID}, approx[p]});
        }
    }

    POMAGMA_INFO("Initializing unary_function cache");
    for (const auto & i : signature().nullary_functions()) {
        const auto & fun = *i->second;
        const uint64_t hash = hash_name(i.first);
        bool inserted = m_unary_cache.insert({
            {hash, BELOW, UNARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){ return above_unary_relation(fun, key); });
        }).second and m_unary_cache.insert({
            {hash, ABOVE, UNARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){ return below_unary_relation(fun, key); });
        }).second and m_unary_cache.insert({
            {hash, NBELOW, UNARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){ return nabove_unary_relation(fun, key); });
        }).second and m_unary_cache.insert({
            {hash, NABOVE, UNARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){ return nbelow_unary_relation(fun, key); });
        }).second;
        POMAGMA_ASSERT(inserted, "hash_conflict");
    }
}

bool Approixmator::refines (
        const Approximation & lhs,
        const Approximation & rhs) const
{
    return m_sets.load(rhs[BELOW]) <= m_sets.load(lhs[BELOW])
       and m_sets.load(rhs[ABOVE]) <= m_sets.load(lhs[ABOVE])
       and m_sets.load(rhs[NBELOW]) <= m_sets.load(lhs[NBELOW])
       and m_sets.load(rhs[NABOVE]) <= m_sets.load(lhs[NABOVE]);
}

} // namespace intervals
} // namespace pomagma
