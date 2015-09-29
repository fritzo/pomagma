#include <pomagma/analyst/intervals.hpp>
#include <functional>
#include <set>

#define POMAGMA_ASSERT1_TROOL(ob)                                           \
    POMAGMA_ASSERT1(                                                        \
        (ob) == 0 or (ob) == m_bot or (ob) == m_identity,                   \
        "bad trool value: " << (ob))

namespace pomagma {
namespace intervals {

inline uint64_t Approximator::hash_name (const std::string & name)
{
    return util::Fingerprint64(name.data(), name.size());
}

namespace {

template<class Map, class Key, class Val>
inline void safe_insert (Map & map, Key key, Val val)
{
    bool inserted = map.insert({key, val}).second;
    POMAGMA_ASSERT(inserted, "hash conflict");
}

} // namespace

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
    m_known(1 + m_item_dim, pending()),
    m_disjoint_cache(
        worker_pool,
        [this](const std::pair<SetId, SetId> & pair){
            return m_sets.load(pair.first).disjoint(m_sets.load(pair.second))
                ? Trool::TRUE
                : Trool::FALSE;
        }),
    m_union_cache(
        worker_pool,
        [this](const std::vector<SetId> & sets){
            const size_t count = sets.size();
            POMAGMA_ASSERT1(2 < count, "too few sets: " << count);
            DenseSet val(m_item_dim);
            val.set_union(sets[0], sets[1]);
            for (size_t i = 2; i < count; ++i) {
                val += sets[i];
            }
            return m_sets.store(std::move(val));
        })
{
    POMAGMA_ASSERT(m_top, "TOP is not defined");
    POMAGMA_ASSERT(m_bot, "BOT is not defined");
    POMAGMA_ASSERT(m_identity, "I is not defined");

    POMAGMA_INFO("Inserting LESS and NLESS in DenseSetStore");
    for (auto iter = m_structure.carrier().iter(); iter.ok(); iter.next()) {
        const Ob ob = * iter;
        m_known[ob][BELOW] = m_sets.store(m_less.get_Rx_set(ob));
        m_known[ob][ABOVE] = m_sets.store(m_less.get_Lx_set(ob));
        m_known[ob][NBELOW] = m_sets.store(m_nless.get_Rx_set(ob));
        m_known[ob][NABOVE] = m_sets.store(m_nless.get_Lx_set(ob));
    }
    m_unknown = interval(m_bot, m_top);
    m_maybe = interval(m_bot, m_identity);
    m_truthy = known(m_identity);
    m_falsey = known(m_bot);

    POMAGMA_INFO("Initializing nullary_function cache");
    for (const auto & i : signature().nullary_functions()) {
        const uint64_t hash = hash_name(i.first);
        Ob ob = i.second->find();
        Approximation approx = ob ? known(ob) : unknown();
        for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
            safe_insert(m_nullary_cache, hash, approx[p]);
        }
    }

    POMAGMA_INFO("Initializing binary_function cache");
    for (const auto & i : signature().binary_functions()) {
        const auto & fun = * i.second;
        const uint64_t hash = hash_name(i.first);
        typedef LazyMap<std::pair<SetId, SetId>, SetId> Map;
        for (Parity p : {ABOVE, BELOW}) {
            safe_insert(m_binary_cache, {hash, LHS_RHS, p}, new Map(
                worker_pool,
                [this, &fun, p](const std::pair<SetId, SetId> & x){
                    return binary_function_lhs_rhs(fun, x.first, x.second, p);
                }));
        }
        for (Parity p : {NABOVE, NBELOW}) {
            safe_insert(m_binary_cache, {hash, LHS_VAL, p}, new Map(
                worker_pool,
                [this, &fun, p](const std::pair<SetId, SetId> & x){
                    return binary_function_lhs_val(fun, x.first, x.second, p);
                }));
            safe_insert(m_binary_cache, {hash, RHS_VAL, p}, new Map(
                worker_pool,
                [this, &fun, p](const std::pair<SetId, SetId> & x){
                    return binary_function_rhs_val(fun, x.first, x.second, p);
                }));
        }
    }

    TODO("Initialize symmetric_function cache");
}

Trool Approximator::lazy_is_valid (const Approximation & approx)
{
    return and_trool(
        lazy_disjoint(approx[BELOW], approx[NBELOW]),
        lazy_disjoint(approx[ABOVE], approx[NABOVE]));
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

inline Trool Approximator::lazy_disjoint (SetId lhs, SetId rhs)
{
    if (not lhs or not rhs) {
        return Trool::MAYBE;
    }
    if (unlikely(lhs == rhs)) {
        return (lhs == m_empty_set) ? Trool::TRUE : Trool::FALSE;
    }
    if (lhs > rhs) {
        std::swap(lhs, rhs);
    }
    return m_disjoint_cache.try_find({lhs, rhs});
}

// this has space complexity O(#constraints * #iterations) cache entries
inline SetId Approximator::lazy_fuse (
    const std::vector<Approximation> & messages,
    Parity parity)
{
    std::set<SetId> sets;
    size_t count = 0;
    for (const auto & message : messages) {
        if (message[parity] == 0) return 0; // wait for pending computations
        if (message[parity] == m_unknown[parity]) continue; // ignore unknowns
        count += sets.insert(message[parity]).second; // ignore duplicates
    }
    if (count == 0) return m_unknown[parity];
    if (count == 1) return * sets.begin();
    return m_union_cache.try_find(std::vector<SetId>(sets.begin(), sets.end()));
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

// Inference rules, in order of appearance
//
//                LESS x y   LESS x z
//   ----------   -------------------
//   LESS x TOP     LESS x RAND y z
//   
//                LESS y x   LESS z x   LESS y x   LESS z x
//   ----------   -------------------   -------------------
//   LESS BOT x     LESS JOIN y z x       LESS RAND y z x
//
void Approximator::lazy_close (Approximation &)
{
    // TODO close under inference rules
}

Approximation Approximator::lazy_fuse (
    const std::vector<Approximation> & messages)
{
    Approximation result = unknown();
    for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
        result[p] = lazy_fuse(messages, p);
    }
    lazy_close(result);
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

Approximation Approximator::lazy_less_lhs_rhs (
    const std::string & name,
    const Approximation & lhs,
    const Approximation & rhs)
{
    Approximation val = pending();
    Trool less = lazy_disjoint(lhs[ABOVE], rhs[BELOW]);
    if (Ob ob = case_trool<Ob>(less, 0, m_bot, m_identity)) {
        val[BELOW] = m_known[trool][BELOW];
        val[NABOVE] = m_known[trool][NABOVE];
    }
    Trool nless = and_trool(
        lazy_disjoint(lhs[BELOW], rhs[NBELOW]),
        lazy_disjoint(lhs[NABOVE], rhs[ABOVE]));
    if (Ob ob = case_trool<Ob>(nless, 0, m_bot, m_identity)) {
        val[ABOVE] = m_known[trool][ABOVE];
        val[NBELOW] = m_known[trool][NBELOW];
    }
    return val; // if both conditions fire, val is inconsistent
}

Approximation Approximator::lazy_nless_lhs_rhs (
    const std::string & name,
    const Approximation & lhs,
    const Approximation & rhs)
{
    Approximation val = pending();
    Trool less = lazy_disjoint(lhs[ABOVE], rhs[BELOW]);
    if (Ob ob = case_trool<Ob>(less, 0, m_bot, m_identity)) {
        val[ABOVE] = m_known[ob][ABOVE];
        val[NBELOW] = m_known[ob][NBELOW];
    }
    Trool nless = and_trool(
        lazy_disjoint(lhs[BELOW], rhs[NBELOW]),
        lazy_disjoint(lhs[NABOVE], rhs[ABOVE]));
    if (Ob ob = case_trool<Ob>(nless, 0, m_bot, m_identity)) {
        val[BELOW] = m_known[ob][BELOW];
        val[NABOVE] = m_known[ob][NABOVE];
    }
    return val; // if both conditions fire, val is inconsistent
}

// LESS f g    LESS x y 
// --------------------
// LESS APP f x APP g y
// 
SetId Approximator::binary_function_lhs_rhs (
    const BinaryFunction & fun,
    SetId lhs,
    SetId rhs,
    Parity parity) const
{
    const DenseSet lhs_set = m_sets.load(lhs); // positive
    const DenseSet rhs_set = m_sets.load(rhs); // positive
    const DenseSet val_set(m_item_dim); // positive
    const DenseSet temp_set(m_item_dim);

    for (auto iter = lhs_set.iter(); iter.ok(); iter.next()) {
        Ob lhs = * iter;

        // optimize for special cases of APP and COMP
        if (Ob lhs_top = fun.find(lhs, m_top)) {
            if (Ob lhs_bot = fun.find(lhs, m_bot)) {
                bool lhs_is_constant = (lhs_top == lhs_bot);
                if (lhs_is_constant) {
                    val_set.raw_insert(lhs_top);
                    continue;
                }
            }
        }

        temp_set.set_insn(rhs_set, fun.get_Lx_set(lhs));
        for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
            Ob rhs = * iter;
            Ob val = fun.find(lhs, rhs);
            val_set.raw_insert(val);
        }
    }

    return m_sets.store(std::move(val_set));
}

SetId Approximator::binary_function_lhs_val (
    const BinaryFunction & fun,
    SetId lhs,
    SetId val,
    Parity parity) const
{
    const DenseSet lhs_set = m_sets.load(lhs); // positive
    const DenseSet val_set = m_sets.load(val); // negative
    const DenseSet rhs_set(m_item_dim);
    const DenseSet temp_set(m_item_dim);

    for (auto iter = lhs_set.iter(); iter.ok(); iter.next()) {
        Ob lhs = * iter;

        // optimize for special cases of APP and COMP
        if (Ob lhs_top = fun.find(lhs, m_top)) {
            if (Ob lhs_bot = fun.find(lhs, m_bot)) {
                bool lhs_is_constant = (lhs_top == lhs_bot);
                if (lhs_is_constant) {
                    val_set.raw_insert(lhs_top);
                    continue;
                }
            }
        }

        temp_set.set_insn(rhs_set, fun.get_Lx_set(lhs));
        for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
            Ob rhs = * iter;
            Ob val = fun.find(lhs, rhs);
            val_set.raw_insert(val);
        }
    }

    return m_sets.store(std::move(val_set));
}

SetId Approximator::binary_function_rhs_val (
    const BinaryFunction & fun,
    SetId rhs,
    SetId val,
    Parity parity) const
{
    TODO("similar to binary_function_lhs_val");
}

} // namespace intervals
} // namespace pomagma
