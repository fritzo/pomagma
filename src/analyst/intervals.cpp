#include <pomagma/analyst/intervals.hpp>
#include <functional>
#include <tuple>
#include <utility>
#include <vector>

namespace pomagma {
namespace intervals {

inline uint64_t Approximator::hash_name (const string & name)
{
    return util::Fingerprint64(name.data(), name.size());
}

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
    m_empty_set(sets.store(std::move(DenseSet(m_item_dim)))),
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

    POMAGMA_INFO("Initializing injective_function cache");
    for (const auto & i : signature().nullary_functions()) {
        const auto & fun = *i->second;
        const uint64_t hash = hash_name(i.first);
        bool inserted = m_injective_cache.insert({
            {hash, BELOW, UNARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){
                    return above_injective_function(fun, key);
                });
        }).second and m_injective_cache.insert({
            {hash, ABOVE, UNARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){
                    return below_injective_function(fun, key);
                });
        }).second and m_injective_cache.insert({
            {hash, NBELOW, UNARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){
                    return nabove_injective_function(fun, key);
                });
        }).second and m_injective_cache.insert({
            {hash, NABOVE, UNARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){
                    return nbelow_injective_function(fun, key);
                });
        }).second;
        POMAGMA_ASSERT(inserted, "hash_conflict");
    }
}

bool Approximator::is_valid (const Approximation & a)
{
    return m_sets.load(a[BELOW]).likely_disjoint(m_sets.load(a[NBELOW])
       and m_sets.load(a[ABOVE]).likely_disjoint(m_sets.load(a[NABOVE]);
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

inline SetId Approximator::lazy_find (
    const std::string & name,
    Parity parity,
    Direction direction,
    SetId arg)
{
    auto i = m_unary_cache.find({hash_name(hash), parity, direction});
    POMAGMA_ASSERT1(i != m_unary_cache.end(), "programmer error");
    return i->second->try_find(arg);
}

inline SetId Approximator::lazy_find (
    const std::string & name,
    Parity parity,
    Direction direction,
    SetId arg0,
    SetId arg1)
{
    auto i = m_binary_cache.find({hash_name(hash), parity, direction});
    POMAGMA_ASSERT1(i != m_binary_cache.end(), "programmer error");
    return i->second->try_find({arg0, arg1});
}

Approximation Approximator::lazy_fuse (
    const std::vector<Approximation> & messages)
{
    Approximation result = pending();
    std::vector<SetId> sets;
    sets.reserve(messages.size());
    for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
        sets.clear();
        for (const auto & message : messages) {
            if (message[p] != m_empty_set) {
                sets.push_back(message[p]);
            }
        }
        std::sort(sets.begin(), sets.end());
        if (sets.empty()) {
            result[p] = m_empty_set;
        } else if (sets.size() == 1) {
            result[p] = sets[0];
        } else if (sets[0] == 0) { // only compute if all sets are available
            result[p] = 0;
        } else {
            result[p] = m_union_cache.try_find(sets);
        }
    }
    return result;
}

Approximation Approximator::lazy_nullary_function (const std::string & name)
{
    auto i = m_nullary_cache.find(hash_name(name));
    POMAGMA_ASSERT(i != m_nullary_cache.end(), "programmer error");
    return i->second;
}

Approximation Approximator::lazy_binary_function_lhs_rhs (
    const std::string & name,
    const Approximation & lhs,
    const Approximation & rhs)
{
    Approximation val = pending();
    for (Parity p : {ABOVE, BELOW}) {
        if (lhs[p] and rhs[p]) {
            val[p] = lazy_find(name, p, LHS_RHS, lhs[p], rhs[p]);
        }
    }
    val[NBELOW] = m_empty_set;
    val[NABOVE] = m_empty_set;
    return val;
}

Approximation Approximator::lazy_binary_function_lhs_val (
    const std::string & name,
    const Approximation & lhs,
    const Approximation & val)
{
    Approximation rhs = pending();
    rhs[BELOW] = m_empty_set;
    rhs[ABOVE] = m_empty_set;
    if (lhs[BELOW] and val[NBELOW]) {
        rhs[NBELOW] = lazy_find(name, NBELOW, LHS_VAL, lhs[BELOW], val[NBELOW]);
    }
    if (lhs[ABOVE] and val[NABOVE]) {
        rhs[NABOVE] = lazy_find(name, NABOVE, LHS_VAL, lhs[ABOVE], val[NABOVE]);
    }
    return rhs;
}

} // namespace intervals
} // namespace pomagma
