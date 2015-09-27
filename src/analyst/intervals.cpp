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
    m_below(1 + m_item_dim),
    m_above(1 + m_item_dim),
    m_nbelow(1 + m_item_dim),
    m_nabove(1 + m_item_dim),
    m_fuse_cache(
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
    m_unknown = interval(m_bot, m_top);

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

    POMAGMA_INFO("Initializing binary_function cache");
    for (const auto & i : signature().binary_functions()) {
        const auto & fun = *i->second;
        const uint64_t hash = hash_name(i.first);
        bool inserted = m_binary_cache.insert({
            {hash, BELOW, BINARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){
                    return above_injective_function(fun, key);
                });
        }).second and m_binary_cache.insert({
            {hash, ABOVE, BINARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){
                    return below_injective_function(fun, key);
                });
        }).second and m_binary_cache.insert({
            {hash, NBELOW, BINARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){
                    return nabove_injective_function(fun, key);
                });
        }).second and m_binary_cache.insert({
            {hash, NABOVE, BINARY_FUNCTION, KEY},
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
    for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
        if (lhs[p] and rhs[p]) { // either set might be pending
            if (not m_sets.load(rhs[p]) <= m_sets.load(lhs[p])) return false;
        }
    }
    return true;
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

// this has space cost O(#constraints * #iterations) cache entries
inline SetId Approximator::lazy_fuse (
    const std::vector<Approximation> & messages,
    Parity parity)
{
    std::set<SetId> sets;
    size_t count = 0;
    for (const auto & message : messages) {
        if (message[parity] == 0) return 0; // wait for pending computations
        if (message[parity] == m_unknown[parity]) continue; // ignore unknowns
        count += sets.insert(message[p]).second; // ignore duplicates
    }
    if (count == 0) return m_unknown[parity];
    if (count == 1) return *sets.begin();
    return m_fuse_cache.try_find(std::vector<SetId>(sets.begin(), sets.end()));
}

Approximation Approximator::lazy_fuse (
    const std::vector<Approximation> & messages)
{
    Approximation result = unknown();
    for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
        result[p] = lazy_fuse(messages, p);
    }
    return result;
}

Approximation Approximator::lazy_binary_function_lhs_rhs (
    const std::string & name,
    const Approximation & lhs,
    const Approximation & rhs)
{
    Approximation val = unknown();
    for (Parity p : {ABOVE, BELOW}) {
        val[p] = (lhs[p] and rhs[p])
               ? lazy_find(name, p, LHS_RHS, lhs[p], rhs[p])
               : 0;
    }
    return val;
}

Approximation Approximator::lazy_binary_function_lhs_val (
    const std::string & name,
    const Approximation & lhs,
    const Approximation & val)
{
    Approximation rhs = unknown();
    rhs[NBELOW] = (lhs[BELOW] and val[NBELOW])
                ? lazy_find(name, NBELOW, LHS_VAL, lhs[BELOW], val[NBELOW])
                : 0;
    rhs[NABOVE] = (lhs[ABOVE] and val[NABOVE])
                ? lazy_find(name, NABOVE, LHS_VAL, lhs[ABOVE], val[NABOVE])
                : 0;
    return rhs;
}

} // namespace intervals
} // namespace pomagma
