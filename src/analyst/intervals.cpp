#include <pomagma/analyst/intervals.hpp>
#include <functional>
#include <set>

#define POMAGMA_INSERT(collection, key, val)                                \
    {                                                                       \
        auto inserted = (collection).insert({(key), (val)});                \
        POMAGMA_ASSERT(inserted.second, "hash conflict");                   \
    }

namespace pomagma {
namespace intervals {

using std::placeholders::_1;

inline uint64_t Approximator::hash_name (const std::string & name)
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
        }),
    m_close_upward_cache(
        worker_pool,
        std::bind(&Approximator::close_upward, this, _1)),
    m_close_downward_cache(
        worker_pool,
        std::bind(&Approximator::close_downward, this, _1))
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
        const std::string & name = i.first;
        Ob ob = i.second->find();
        Approximation approx = ob ? known(ob) : unknown();
        POMAGMA_INSERT(m_nullary_cache, name, approx);
    }

    POMAGMA_INFO("Initializing binary_function cache");
    for (const auto & i : signature().binary_functions()) {
        const auto & fun = * i.second;
        const uint64_t hash = hash_name(i.first);
        typedef SetPairToSetCache Cache;
        POMAGMA_INSERT(
            m_binary_cache,
            CacheKey(hash, LHS_RHS),
            new Cache(
                worker_pool,
                [this, &fun](const std::pair<SetId, SetId> & x){
                    return function_lhs_rhs(fun, x.first, x.second);
                }));
        POMAGMA_INSERT(
            m_binary_cache,
            CacheKey(hash, LHS_VAL),
            new Cache(
                worker_pool,
                [this, &fun](const std::pair<SetId, SetId> & x){
                    return function_lhs_val(fun, x.first, x.second);
                }));
        POMAGMA_INSERT(
            m_binary_cache,
            CacheKey(hash, RHS_VAL),
            new Cache(
                worker_pool,
                [this, &fun](const std::pair<SetId, SetId> & x){
                    return function_rhs_val(fun, x.first, x.second);
                }));
    }

    POMAGMA_INFO("Initializing symmetric_function cache");
    for (const auto & i : signature().symmetric_functions()) {
        const auto & fun = * i.second;
        const uint64_t hash = hash_name(i.first);
        typedef SetPairToSetCache Cache;
        POMAGMA_INSERT(
            m_binary_cache,
            CacheKey(hash, LHS_RHS),
            new Cache(
                worker_pool,
                [this, &fun](const std::pair<SetId, SetId> & x){
                    return function_lhs_rhs(fun, x.first, x.second);
                }));
        POMAGMA_INSERT(
            m_binary_cache,
            CacheKey(hash, LHS_VAL),
            new Cache(
                worker_pool,
                [this, &fun](const std::pair<SetId, SetId> & x){
                    return function_lhs_val(fun, x.first, x.second);
                }));
        POMAGMA_INSERT(
            m_binary_cache,
            CacheKey(hash, RHS_VAL),
            new Cache(
                worker_pool,
                [this, &fun](const std::pair<SetId, SetId> & x){
                    return function_rhs_val(fun, x.first, x.second);
                }));
    }
}

Trool Approximator::lazy_is_valid (const Approximation & approx)
{
    return and_trool(
        lazy_disjoint(approx[BELOW], approx[NBELOW]),
        lazy_disjoint(approx[ABOVE], approx[NABOVE]));
}

bool Approximator::refines (
        const Approximation & lhs,
        const Approximation & rhs) const
{
    for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
        if (lhs[p] and rhs[p]) { // either set might be pending
            if (not (m_sets.load(rhs[p]) <= m_sets.load(lhs[p]))) return false;
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
    Direction direction,
    SetId arg0,
    SetId arg1)
{
    auto i = m_binary_cache.find(CacheKey{hash_name(name), direction});
    POMAGMA_ASSERT1(i != m_binary_cache.end(), "programmer error");
    return i->second->try_find({arg0, arg1});
}

//                LESS x y   LESS y z
//   ----------   -------------------
//   LESS x TOP         LESS x z
SetId Approximator::close_upward (SetId set) const
{
    const DenseSet original = m_sets.load(set);
    DenseSet result(m_item_dim);

    result.raw_insert(m_top);
    for (auto iter = original.iter(); iter.ok(); iter.next()) {
        Ob ob = * iter;
        if (not result.contains(ob)) {
            result += m_less.get_Lx_set(ob);
        }
    }

    return m_sets.store(std::move(result));
}

//                LESS x y   LESS y z
//   ----------   -------------------
//   LESS BOT x         LESS x z
SetId Approximator::close_downward (SetId set) const
{
    const DenseSet original = m_sets.load(set);
    DenseSet result(m_item_dim);

    result.raw_insert(m_bot);
    for (auto iter = original.iter(); iter.ok(); iter.next()) {
        Ob ob = * iter;
        if (not result.contains(ob)) {
            result += m_less.get_Rx_set(ob);
        }
    }

    return m_sets.store(std::move(result));
}

Approximation Approximator::lazy_close (const Approximation & approx)
{
    Approximation result = pending();
    for (Parity p : {BELOW, NABOVE}) {
        result[p] = m_close_downward_cache.try_find(approx[p]);
    }
    for (Parity p : {ABOVE, NBELOW}) {
        result[p] = m_close_upward_cache.try_find(approx[p]);
    }
    return result;
}

Approximation Approximator::lazy_fuse (
    const std::vector<Approximation> & messages)
{
    Approximation result = unknown();
    for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
        result[p] = lazy_fuse(messages, p);
    }
    return lazy_close(result);
}

Approximation Approximator::lazy_binary_function_lhs_rhs (
    const std::string & name,
    const Approximation & lhs,
    const Approximation & rhs)
{
    Approximation val = unknown();
    for (Parity p : {ABOVE, BELOW}) {
        val[p] = (lhs[p] and rhs[p])
               ? lazy_find(name, LHS_RHS, lhs[p], rhs[p])
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
                ? lazy_find(name, LHS_VAL, lhs[BELOW], val[NBELOW])
                : 0;
    rhs[NABOVE] = (lhs[ABOVE] and val[NABOVE])
                ? lazy_find(name, LHS_VAL, lhs[ABOVE], val[NABOVE])
                : 0;
    return rhs;
}

Approximation Approximator::lazy_binary_function_rhs_val (
    const std::string & name,
    const Approximation & rhs,
    const Approximation & val)
{
    Approximation lhs = unknown();
    lhs[NBELOW] = (rhs[BELOW] and val[NBELOW])
                ? lazy_find(name, RHS_VAL, rhs[BELOW], val[NBELOW])
                : 0;
    lhs[NABOVE] = (rhs[ABOVE] and val[NABOVE])
                ? lazy_find(name, RHS_VAL, rhs[ABOVE], val[NABOVE])
                : 0;
    return rhs;
}

Approximation Approximator::lazy_less_lhs_rhs (
    const Approximation & lhs,
    const Approximation & rhs)
{
    Approximation val = pending();
    Trool less = lazy_disjoint(lhs[ABOVE], rhs[BELOW]);
    if (Ob ob = case_trool<Ob>(less, 0, m_bot, m_identity)) {
        val[BELOW] = m_known[ob][BELOW];
        val[NABOVE] = m_known[ob][NABOVE];
    }
    Trool nless = and_trool(
        lazy_disjoint(lhs[BELOW], rhs[NBELOW]),
        lazy_disjoint(lhs[NABOVE], rhs[ABOVE]));
    if (Ob ob = case_trool<Ob>(nless, 0, m_bot, m_identity)) {
        val[ABOVE] = m_known[ob][ABOVE];
        val[NBELOW] = m_known[ob][NBELOW];
    }
    return val; // if both conditions fire, val is inconsistent
}

Approximation Approximator::lazy_nless_lhs_rhs (
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
template<class Function>
SetId Approximator::function_lhs_rhs (
    const Function & fun,
    SetId lhs,
    SetId rhs) const
{
    const DenseSet lhs_set = m_sets.load(lhs); // positive
    const DenseSet rhs_set = m_sets.load(rhs); // positive
    DenseSet val_set(m_item_dim); // positive
    DenseSet temp_set(m_item_dim);

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

// LESS f g   NLESS APP f x APP g y
// --------------------------------
//            NLESS x y 
template<class Function>
SetId Approximator::function_lhs_val (
    const Function & fun,
    SetId lhs,
    SetId val) const
{
    const DenseSet lhs_set = m_sets.load(lhs); // positive
    const DenseSet val_set = m_sets.load(val); // negative
    DenseSet rhs_set(m_item_dim); // negative

    // slow naive implementation
    for (auto iter = lhs_set.iter(); iter.ok(); iter.next()) {
        Ob lhs = * iter;
        for (auto iter = fun.iter_lhs(lhs); iter.ok(); iter.next()) {
            Ob rhs = * iter;
            Ob val = fun.find(lhs, rhs);
            if (val_set.contains(val)) {
                rhs_set.raw_insert(rhs);
            }
        }
    }

    return m_sets.store(std::move(rhs_set));
}

// NLESS APP f x APP g y   LESS x y
// --------------------------------
//             NLESS f g
template<class Function>
SetId Approximator::function_rhs_val (
    const Function & fun,
    SetId rhs,
    SetId val) const
{
    const DenseSet rhs_set = m_sets.load(rhs); // positive
    const DenseSet val_set = m_sets.load(val); // negative
    DenseSet lhs_set(m_item_dim); // negative

    // slow naive implementation
    for (auto iter = rhs_set.iter(); iter.ok(); iter.next()) {
        Ob rhs = * iter;
        for (auto iter = fun.iter_rhs(rhs); iter.ok(); iter.next()) {
            Ob lhs = * iter;
            Ob val = fun.find(lhs, rhs);
            if (val_set.contains(val)) {
                lhs_set.raw_insert(lhs);
            }
        }
    }

    return m_sets.store(std::move(lhs_set));
}

} // namespace intervals
} // namespace pomagma
