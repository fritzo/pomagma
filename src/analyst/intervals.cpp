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
    m_known(1 + m_item_dim, pending()),
    m_disjoint_cache(
        worker_pool,
        [this](const std::pair<SetId, SetId> & pair){
            return m_sets.load(pair.first).disjoint(m_sets.load(pair.second))
                ? m_identity // truthy
                : m_bot; // falsey
        }),
    m_union_cache(
        worker_pool,
        [this](const std::pair<SetId, SetId> & pair){
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
            m_nullary_cache.insert(
                {{hash, p, NULLARY_FUNCTION, VOID}, approx[p]});
        }
    }

    TODO("Initialize injective_function cache");

    POMAGMA_INFO("Initializing binary_function cache");
    for (const auto & i : signature().binary_functions()) {
        const auto & fun = *i->second;
        const uint64_t hash = hash_name(i.first);
        safe_insert(
            m_binary_cache
            {hash, BELOW, BINARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){
                    return above_binary_function(fun, key);
                }));
        safe_insert(
            m_binary_cache,
            {hash, ABOVE, BINARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){
                    return below_binary_function(fun, key);
                }));
        safe_insert(
            m_binary_cache.insert,
            {hash, NBELOW, BINARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){
                    return nabove_binary_function(fun, key);
                }));
        safe_insert(
            m_binary_cache,
            {hash, NABOVE, BINARY_FUNCTION, KEY},
            new LazyMap<SetId, SetId>(
                worker_pool,
                [this](SetId key){
                    return nbelow_binary_function(fun, key);
                }));
        POMAGMA_ASSERT(inserted, "hash conflict");
    }

    TODO("Initialize symmetric_function cache");

    POMAGMA_INFO("Initializing less cache");
    {
        const uint64_t hash = hash_name("LESS");
        safe_insert(
            m_binary_cache,
            {hash, BELOW, BINARY_RELATION, LHS_RHS},
            new LazyMap<SetId, std::pair<SetId, SetId>>(
                worker_pool,
                [this](const std::pair<SetId, SetId> & lhs_rhs){
                    DenseSet lhs = m_sets.load(lhs_rhs.first);
                    DenseSet rhs = m_sets.load(lhs_rhs.second);
                    return (lhs.disjoint(rhs) ? m_maybe : m_falsey)[BELOW];
                }));
        safe_insert(
            m_binary_cache,
            {hash, BELOW, BINARY_RELATION, LHS_RHS},
            new LazyMap<SetId, std::pair<SetId, SetId>>(
                worker_pool,
                [this](const std::pair<SetId, SetId> & lhs_rhs){
                    DenseSet lhs = m_sets.load(lhs_rhs.first);
                    DenseSet rhs = m_sets.load(lhs_rhs.second);
                    return (lhs.disjoint(rhs) ? m_maybe : m_falsey)[BELOW];
                }));
    }
}

size_t Approximator::test ()
{
    and_trool_test();
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

inline Ob Approximator::lazy_disjoint (SetId lhs, SetId rhs)
{
    Ob trool = m_disjoint_cache.try_find({lhs, rhs});
    POMAGMA_ASSERT1_TROOL(trool);
    return trool;
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
    if (count == 1) return *sets.begin();
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

inline Ob Approximator::and_trool (Ob lhs, Ob rhs) const
{
    POMAGMA_ASSERT1_TROOL(lhs);
    POMAGMA_ASSERT1_TROOL(rhs);
    if (lhs == m_identity or rhs == m_identity) return m_identity;
    if (lhs == 0 or rhs == 0) return 0;
    return m_bot;
}

void Approximator::and_trool_test () const
{
    const Ob I = m_identity;
    const Ob BOT = m_bot;
    const std::vector<std::tuple<Ob, Ob, Ob>> examples = {
        {0, 0, 0},
        {0, BOT, 0},
        {0, I, I},
        {BOT, 0, 0},
        {BOT, BOT, BOT},
        {BOT, I, I},
        {I, 0, I},
        {I, BOT, I},
        {I, I, I}
    };
    Ob lhs, rhs, expected;
    for (std::tie<lhs, rhs, expected> : examples) {
        Ob actual = and_trool(lhs, rhs);
        POMAGMA_ASSERT1_TROOL(actual);
        POMAGMA_ASSERT(
            actual == expected,
            "expected and_trool(" << lhs << ", " << rhs << ") == " << expected
            << ", actual " << actual);
    }
}

Approximation Approximator::lazy_less_lhs_rhs (
    const std::string & name,
    const Approximation & lhs,
    const Approximation & rhs)
{
    Approximation val = pending();
    if (Ob trool = lazy_disjoint(lhs[ABOVE], rhs[BELOW])) {
        POMAGMA_ASSERT1_TROOL(trool);
        val[BELOW] = m_known[trool][BELOW];
        val[NABOVE] = m_known[trool][NABOVE];
    }
    Ob trool1 = lazy_disjoint(lhs[BELOW], rhs[NBELOW]);
    Ob trool2 = lazy_disjoint(lhs[NABOVE], rhs[ABOVE]);
    if (Ob trool = and_trool(trool1, trool2)) {
        POMAGMA_ASSERT1_TROOL(trool);
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
    if (Ob trool = lazy_disjoint(lhs[ABOVE], rhs[BELOW])) {
        POMAGMA_ASSERT1_TROOL(trool);
        val[ABOVE] = m_known[trool][ABOVE];
        val[NBELOW] = m_known[trool][NBELOW];
    }
    Ob trool1 = lazy_disjoint(lhs[BELOW], rhs[NBELOW]);
    Ob trool2 = lazy_disjoint(lhs[NABOVE], rhs[ABOVE]);
    if (Ob trool = and_trool(trool1, trool2)) {
        POMAGMA_ASSERT1_TROOL(trool);
        val[BELOW] = m_known[trool][BELOW];
        val[NABOVE] = m_known[trool][NABOVE];
    }
    return val; // if both conditions fire, val is inconsistent
}

} // namespace intervals
} // namespace pomagma
