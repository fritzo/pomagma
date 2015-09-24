#include <pomagma/analyst/intervals.hpp>
#include <functional>
#include <tuple>
#include <utility>
#include <vector>

namespace pomagma {
namespace intervals {

Approximator::Approximator (Structure & structure, DenseSetStore & sets) :
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
    m_cache(
        std::thread::hardware_concurrency(),
        [this](const Term & term){ return compute(term); })
{
    POMAGMA_ASSERT(m_top, "TOP is not defined");
    POMAGMA_ASSERT(m_bot, "BOT is not defined");
    POMAGMA_ASSERT(m_identity, "I is not defined");

    initialize_sets();
    initialize_cache();
}

void Approximator::initialize_sets ()
{
    POMAGMA_INFO("Inserting LESS and NLESS in DenseSetStore");
    for (auto iter = m_structure.carrier().iter(); iter.ok(); iter.next()) {
        const Ob ob = * iter;
        m_below[ob] = m_sets.store(m_less.get_Rx_set(ob));
        m_above[ob] = m_sets.store(m_less.get_Lx_set(ob));
        m_nbelow[ob] = m_sets.store(m_nless.get_Rx_set(ob));
        m_nabove[ob] = m_sets.store(m_nless.get_Lx_set(ob));
    }
}

void Approximator::initialize_cache ()
{
    POMAGMA_INFO("Inserting structure in LazyMap");
    const std::vector<std::pair<Term::Parity, const std::vector<Ob>>> bounds =
    {
        {Term::BELOW, & m_below},
        {Term::ABOVE, & m_above},
        {Term::NBELOW, & m_nbelow},
        {Term::NABOVE, & m_nabove}
    };
    const std::vector<Ob> * bound;
    Term term;

    term.arity = Term::NULLARY_FUNCTION;
    for (const auto & fun : signature().nullary_functions()) {
        POMAGMA_INFO("Inserting " << fun.first << " in LazyMap");
        term.name_hash = util::Fingerprint64(fun.first);
        term.args[0] = 0;
        term.args[1] = 0;
        if (Ob val = fun.second.find()) {
            for (std::tie(term.parity, bound) : bounds) {
                m_cache.unsafe_insert(term, *bound[val]);
            }
        }
    }

    term.arity = Term::INJECTIVE_FUNCTION;
    for (const auto & fun : signature().injective_functions()) {
        POMAGMA_INFO("Inserting " << fun.first << " in LazyMap");
        term.name_hash = util::Fingerprint64(fun.first);
        term.args[1] = 0;
        for (auto key = fun.second.iter(); key.ok(); key.next()) {
            const Ob val = fun.second.find(*key);
            for (std::tie(term.parity, bound) : bounds) {
                term.args[0] = *bound[*key];
                m_cache.unsafe_insert(term, *bound[val]);
            }
        }
    }

    term.arity = Term::BINARY_FUNCTION;
    for (const auto & fun : signature().binary_functions()) {
        POMAGMA_INFO("Inserting " << fun.first << " in LazyMap");
        term.name_hash = util::Fingerprint64(fun.first);
        for (auto lhs = m_structure.carrier().iter(); lhs.ok(); lhs.next()) {
            for (auto rhs = fun.second.iter_lhs(*lhs); rhs.ok(); rhs.next()) {
                const Ob val = fun.second.find(*lhs, *rhs);
                for (std::tie(term.parity, bound) : bounds) {
                    term.args[0] = *bound[*lhs];
                    term.args[1] = *bound[*rhs];
                    m_cache.unsafe_insert(term, *bound[val]);
                }
            }
        }
    }

    term.arity = Term::SYMMETRIC_FUNCTION;
    for (const auto & fun : signature().symmetric_functions()) {
        POMAGMA_INFO("Inserting " << fun.first << " in LazyMap");
        term.name_hash = util::Fingerprint64(fun.first);
        for (auto lhs = m_structure.carrier().iter(); lhs.ok(); lhs.next()) {
            for (auto rhs = fun.second.iter_lhs(*lhs); rhs.ok(); rhs.next()) {
                const Ob val = fun.second.find(*lhs, *rhs);
                for (std::tie(term.parity, bound) : bounds) {
                    term.args[0] = *bound[*lhs];
                    term.args[1] = *bound[*rhs];
                    m_cache.unsafe_insert(term, *bound[val]);
                }
            }
        }
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
