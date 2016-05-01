#include <pomagma/analyst/intervals.hpp>
#include <functional>
#include <set>

#define POMAGMA_INSERT(collection, key, val)                 \
    {                                                        \
        auto inserted = (collection).insert({(key), (val)}); \
        POMAGMA_ASSERT(inserted.second, "hash conflict");    \
    }

namespace pomagma {
namespace intervals {

inline uint64_t Approximator::hash_name(const std::string& name) {
    return util::Fingerprint64(name.data(), name.size());
}

Approximator::Approximator(Structure& structure, DenseSetStore& sets,
                           WorkerPool& worker_pool)
    :  // structure
      m_structure(structure),
      m_item_dim(structure.carrier().item_dim()),
      m_top(structure.nullary_function("TOP").find()),
      m_bot(structure.nullary_function("BOT").find()),
      m_less(structure.binary_relation("LESS")),
      m_nless(structure.binary_relation("NLESS")),
      // dense set stores
      m_sets(sets),
      m_empty_set(sets.store(std::move(DenseSet(m_item_dim)))),
      m_known(1 + m_item_dim),
      m_unknown(),
      // lazy map caches
      m_disjoint_cache(worker_pool,
                       [this](const std::pair<SetId, SetId>& pair) {
          return m_sets.load(pair.first).disjoint(m_sets.load(pair.second))
                     ? Trool::TRUE
                     : Trool::FALSE;
      }),
      m_union_cache(worker_pool, [this](const std::vector<SetId>& sets) {
          const size_t count = sets.size();
          POMAGMA_ASSERT1(count >= 2, "too few sets: " << count);
          DenseSet val(m_item_dim);
          val.set_union(m_sets.load(sets[0]), m_sets.load(sets[1]));
          for (size_t i = 2; i < count; ++i) {
              val += m_sets.load(sets[i]);
          }
          return m_sets.store(std::move(val));
      }),
      m_nullary_cache(),
      m_binary_cache() {
    POMAGMA_ASSERT(m_top, "TOP is not defined");
    POMAGMA_ASSERT(m_bot, "BOT is not defined");

    POMAGMA_INFO("Inserting LESS and NLESS in DenseSetStore");
    for (auto iter = m_structure.carrier().iter(); iter.ok(); iter.next()) {
        const Ob ob = *iter;
        m_known[ob][ABOVE] = m_sets.store(m_less.get_Lx_set(ob));
        m_known[ob][BELOW] = m_sets.store(m_less.get_Rx_set(ob));
        m_known[ob][NABOVE] = m_sets.store(m_nless.get_Lx_set(ob));
        m_known[ob][NBELOW] = m_sets.store(m_nless.get_Rx_set(ob));
    }
    m_unknown[ABOVE] = m_known[m_top][ABOVE];
    m_unknown[BELOW] = m_known[m_bot][BELOW];
    m_unknown[NABOVE] = m_empty_set;
    m_unknown[NBELOW] = m_empty_set;

    POMAGMA_INFO("Initializing nullary_function cache");
    for (const auto& i : signature().nullary_functions()) {
        const std::string& name = i.first;
        Ob ob = i.second->find();
        Approximation approx = ob ? known(ob) : unknown();
        POMAGMA_INSERT(m_nullary_cache, name, approx);
    }

    POMAGMA_INFO("Initializing binary_function cache");
    for (const auto& i : signature().binary_functions()) {
        const auto& fun = *i.second;
        const uint64_t hash = hash_name(i.first);
        typedef SetPairToSetCache Cache;
        for (Parity p : {ABOVE, BELOW}) {
            POMAGMA_INSERT(
                m_binary_cache, CacheKey(hash, VAL, p),
                new Cache(worker_pool,
                          [this, &fun, p](const std::pair<SetId, SetId>& x) {
                    return function_lhs_rhs(fun, x.first, x.second, p);
                }));
        }
        for (Parity p : {NABOVE, NBELOW}) {
            POMAGMA_INSERT(
                m_binary_cache, CacheKey(hash, RHS, p),
                new Cache(worker_pool,
                          [this, &fun, p](const std::pair<SetId, SetId>& x) {
                    return function_lhs_val(fun, x.first, x.second, p);
                }));
            POMAGMA_INSERT(
                m_binary_cache, CacheKey(hash, LHS, p),
                new Cache(worker_pool,
                          [this, &fun, p](const std::pair<SetId, SetId>& x) {
                    return function_rhs_val(fun, x.first, x.second, p);
                }));
        }
    }

    POMAGMA_INFO("Initializing symmetric_function cache");
    for (const auto& i : signature().symmetric_functions()) {
        const auto& fun = *i.second;
        const uint64_t hash = hash_name(i.first);
        typedef SetPairToSetCache Cache;
        for (Parity p : {ABOVE, BELOW}) {
            POMAGMA_INSERT(
                m_binary_cache, CacheKey(hash, VAL, p),
                new Cache(worker_pool,
                          [this, &fun, p](const std::pair<SetId, SetId>& x) {
                    return function_lhs_rhs(fun, x.first, x.second, p);
                }));
        }
        for (Parity p : {NABOVE, NBELOW}) {
            auto* cache = new Cache(
                worker_pool, [this, &fun, p](const std::pair<SetId, SetId>& x) {
                    return function_lhs_val(fun, x.first, x.second, p);
                });
            POMAGMA_INSERT(m_binary_cache, CacheKey(hash, RHS, p), cache);
            POMAGMA_INSERT(m_binary_cache, CacheKey(hash, LHS, p), cache);
        }
    }
}

bool Approximator::expensive_refines(const Approximation& lhs,
                                     const Approximation& rhs) const {
    for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
        if (lhs[p] and rhs[p]) {  // either set might be pending
            if (not(m_sets.load(rhs[p]) <= m_sets.load(lhs[p]))) return false;
        }
    }
    return true;
}

Trool Approximator::lazy_is_valid(const Approximation& approx) {
    return and_trool(lazy_disjoint(approx[ABOVE], approx[NABOVE]),
                     lazy_disjoint(approx[BELOW], approx[NBELOW]));
}

inline Trool Approximator::lazy_disjoint(SetId lhs, SetId rhs) {
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
inline SetId Approximator::lazy_fuse(const std::vector<Approximation>& messages,
                                     Parity parity) {
    std::set<SetId> sets;
    for (const auto& message : messages) {
        if (message[parity] == 0) return 0;  // wait for pending computations
        if (message[parity] == m_unknown[parity]) continue;  // ignore unknowns
        sets.insert(message[parity]);
    }
    if (sets.size() == 0) return m_unknown[parity];
    if (sets.size() == 1) return *sets.begin();
    return m_union_cache.try_find(std::vector<SetId>(sets.begin(), sets.end()));
}

Approximation Approximator::lazy_fuse(
    const std::vector<Approximation>& messages) {
    Approximation result;
    for (Parity p : {ABOVE, BELOW, NABOVE, NBELOW}) {
        result[p] = lazy_fuse(messages, p);
    }
    return result;
}

inline SetId Approximator::lazy_find(const std::string& name, Target target,
                                     Parity parity, SetId arg0, SetId arg1) {
    auto i = m_binary_cache.find(CacheKey{hash_name(name), target, parity});
    POMAGMA_ASSERT1(i != m_binary_cache.end(), "programmer error");
    return i->second->try_find({arg0, arg1});
}

Approximation Approximator::lazy_binary_function_lhs_rhs(
    const std::string& name, const Approximation& lhs,
    const Approximation& rhs) {
    Approximation val = unknown();
    for (Parity p : {ABOVE, BELOW}) {
        val[p] =
            (lhs[p] and rhs[p]) ? lazy_find(name, VAL, p, lhs[p], rhs[p]) : 0;
    }
    return val;
}

Approximation Approximator::lazy_binary_function_lhs_val(
    const std::string& name, const Approximation& lhs,
    const Approximation& val) {
    Approximation rhs = unknown();
    rhs[NABOVE] = (lhs[ABOVE] and val[NABOVE])
                      ? lazy_find(name, RHS, NABOVE, lhs[ABOVE], val[NABOVE])
                      : 0;
    rhs[NBELOW] = (lhs[BELOW] and val[NBELOW])
                      ? lazy_find(name, RHS, NBELOW, lhs[BELOW], val[NBELOW])
                      : 0;
    return rhs;
}

Approximation Approximator::lazy_binary_function_rhs_val(
    const std::string& name, const Approximation& rhs,
    const Approximation& val) {
    Approximation lhs = unknown();
    lhs[NABOVE] = (rhs[ABOVE] and val[NABOVE])
                      ? lazy_find(name, LHS, NABOVE, rhs[ABOVE], val[NABOVE])
                      : 0;
    lhs[NBELOW] = (rhs[BELOW] and val[NBELOW])
                      ? lazy_find(name, LHS, NBELOW, rhs[BELOW], val[NBELOW])
                      : 0;
    return lhs;
}

inline void Approximator::convex_insert(DenseSet& set, Ob ob,
                                        bool upward) const {
    if (not set.contains(ob)) {
        set += upward ? m_less.get_Lx_set(ob) : m_less.get_Rx_set(ob);
    }
}

// LESS f g    LESS x y                             LESS x y    LESS y z
// --------------------   ----------   ----------   --------------------
// LESS APP f x APP g y   LESS BOT x   LESS x TOP         LESS x z
template <class Function>
SetId Approximator::function_lhs_rhs(const Function& fun, SetId lhs, SetId rhs,
                                     Parity parity) const {
    POMAGMA_ASSERT1(lhs, "lhs is undefined");
    POMAGMA_ASSERT1(rhs, "rhs is undefined");
    POMAGMA_ASSERT1(parity == ABOVE or parity == BELOW, "invalid parity");
    const bool upward = (parity == ABOVE);
    const DenseSet lhs_set = m_sets.load(lhs);  // positive
    const DenseSet rhs_set = m_sets.load(rhs);  // positive
    DenseSet val_set(m_item_dim);               // positive

    const Ob optimum = upward ? m_top : m_bot;
    POMAGMA_ASSERT1(lhs_set.contains(optimum), "invalid lhs set");
    POMAGMA_ASSERT1(rhs_set.contains(optimum), "invalid rhs set");
    val_set.insert(optimum);

    DenseSet temp_set(m_item_dim);
    for (auto iter = lhs_set.iter(); iter.ok(); iter.next()) {
        Ob lhs = *iter;

        // optimize for constant functions
        if (Ob lhs_top = fun.find(lhs, m_top)) {
            if (Ob lhs_bot = fun.find(lhs, m_bot)) {
                if (lhs_top == lhs_bot) {
                    convex_insert(val_set, lhs_top, upward);
                    continue;
                }
            }
        }

        temp_set.set_insn(rhs_set, fun.get_Lx_set(lhs));
        for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
            Ob rhs = *iter;
            Ob val = fun.find(lhs, rhs);
            convex_insert(val_set, val, upward);
        }
    }

    return m_sets.store(std::move(val_set));
}

// LESS f g   NLESS APP f x APP g y
// --------------------------------
//            NLESS x y
//
// NLESS x z    LESS y z    LESS x y    NLESS x z
// ---------------------    ---------------------
//       NLESS x y                NLESS y z
template <class Function>
SetId Approximator::function_lhs_val(const Function& fun, SetId lhs, SetId val,
                                     Parity parity) const {
    POMAGMA_ASSERT1(lhs, "lhs is undefined");
    POMAGMA_ASSERT1(val, "val is undefined");
    POMAGMA_ASSERT1(parity == NABOVE or parity == NBELOW, "invalid parity");
    const bool upward = (parity == NBELOW);
    const DenseSet& support = m_structure.carrier().support();
    const DenseSet lhs_set = m_sets.load(lhs);  // positive
    const DenseSet val_set = m_sets.load(val);  // negative
    DenseSet rhs_set(m_item_dim);               // negative

    for (auto iter = support.iter_diff(rhs_set); iter.ok(); iter.next()) {
        Ob rhs = *iter;
        if (unlikely(rhs_set.contains(rhs))) continue;  // iterator latency
        for (auto iter = fun.get_Rx_set(rhs).iter_insn(lhs_set); iter.ok();
             iter.next()) {
            Ob lhs = *iter;
            Ob val = fun.find(lhs, rhs);
            if (val_set.contains(val)) {
                convex_insert(rhs_set, rhs, upward);
                break;
            }
        }
    }

    return m_sets.store(std::move(rhs_set));
}

// NLESS APP f x APP g y   LESS x y
// --------------------------------
//             NLESS f g
//
// NLESS x z    LESS y z    LESS x y    NLESS x z
// ---------------------    ---------------------
//       NLESS x y                NLESS y z
template <class Function>
SetId Approximator::function_rhs_val(const Function& fun, SetId rhs, SetId val,
                                     Parity parity) const {
    POMAGMA_ASSERT1(rhs, "rhs is undefined");
    POMAGMA_ASSERT1(val, "val is undefined");
    POMAGMA_ASSERT1(parity == NABOVE or parity == NBELOW, "invalid parity");
    const bool upward = (parity == NBELOW);
    const DenseSet& support = m_structure.carrier().support();
    const DenseSet rhs_set = m_sets.load(rhs);  // positive
    const DenseSet val_set = m_sets.load(val);  // negative
    DenseSet lhs_set(m_item_dim);               // negative

    for (auto iter = support.iter_diff(lhs_set); iter.ok(); iter.next()) {
        Ob lhs = *iter;
        if (unlikely(lhs_set.contains(lhs))) continue;  // iterator latency
        for (auto iter = fun.get_Lx_set(lhs).iter_insn(rhs_set); iter.ok();
             iter.next()) {
            Ob rhs = *iter;
            Ob val = fun.find(lhs, rhs);
            if (val_set.contains(val)) {
                convex_insert(lhs_set, lhs, upward);
                break;
            }
        }
    }

    return m_sets.store(std::move(lhs_set));
}

}  // namespace intervals
}  // namespace pomagma
