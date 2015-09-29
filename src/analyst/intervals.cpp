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
    m_sets(sets),
    m_below(1 + m_item_dim),
    m_above(1 + m_item_dim),
    m_nbelow(1 + m_item_dim),
    m_nabove(1 + m_item_dim),
    m_cache(worker_pool, [this](const Term & term){ return compute(term); })
{
    POMAGMA_ASSERT(m_top, "TOP is not defined");
    POMAGMA_ASSERT(m_bot, "BOT is not defined");
    POMAGMA_ASSERT(m_identity, "I is not defined");

    POMAGMA_INFO("Inserting LESS and NLESS in DenseSetStore");
    for (auto iter = m_structure.carrier().iter(); iter.ok(); iter.next()) {
        const Ob ob = * iter;
        m_below[ob] = m_sets.store(m_less.get_Rx_set(ob));
        m_above[ob] = m_sets.store(m_less.get_Lx_set(ob));
        m_nbelow[ob] = m_sets.store(m_nless.get_Rx_set(ob));
        m_nabove[ob] = m_sets.store(m_nless.get_Lx_set(ob));
    }
}

SetId Approximator::compute (const Term & term)
{
    switch (term.parity) {
        default: POMAGMA_ERROR("TODO");
    }
}

} // namespace intervals
} // namespace pomagma
