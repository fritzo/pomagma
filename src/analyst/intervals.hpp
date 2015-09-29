#pragma once

#include <pomagma/atlas/macro/structure_impl.hpp>
#include <pomagma/atlas/macro/util.hpp>
#include <pomagma/util/dense_set_store.hpp>
#include <pomagma/util/lazy_map.hpp>
#include <pomagma/util/trool.hpp>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

// declared in pomagma/vendor/farmhash/farmhash.h
namespace util { uint64_t Fingerprint64(const char * s, size_t len); }

namespace pomagma {
namespace intervals {

template<class T>
struct PodHash
{
    uint64_t operator() (const T & x) const
    {
        return util::Fingerprint64(
            reinterpret_cast<const char *>(& x),
            sizeof(T));
    }
};

template<class T>
struct VectorPodHash
{
    uint64_t operator() (const std::vector<T> & x) const
    {
        return util::Fingerprint64(
            reinterpret_cast<const char *>(x.data()),
            x.size() * sizeof(T));
    }
};

enum Parity { ABOVE, BELOW, NABOVE, NBELOW };
enum Direction { VOID, KEY, VAL, LHS, RHS, LHS_RHS, LHS_VAL, RHS_VAL };
enum Arity {
    NULLARY_FUNCTION,
    INJECTIVE_FUNCTION,
    BINARY_FUNCTION,
    SYMMETRIC_FUNCTION,
    // no UNARY_RELATION
    BINARY_RELATION
};

struct Approximation
{
    SetId bounds[4]; // one for each Parity
    SetId & operator[] (Parity p) { return bounds[p]; }
    SetId operator[] (Parity p) const { return bounds[p]; }
};

class Approximator
{
public:

    Approximator (
            Structure & structure,
            DenseSetStore & sets,
            WorkerPool & worker_pool);

    size_t test () {} // TODO
    void validate (const Approximation & approx);
    Trool lazy_is_valid (const Approximation & approx);
    bool refines (const Approximation & lhs, const Approximation & rhs) const;

    Approximation pending () const { return {0, 0, 0, 0}; }
    Approximation known (Ob ob) const { return m_known[ob]; }
    Approximation unknown () const { return m_unknown; }
    Approximation interval (Ob lb, Ob ub) const;
    Approximation maybe () const { return m_maybe; }
    Approximation truthy () const { return m_truthy; }
    Approximation falsey () const { return m_falsey; }
    Approximation nullary_function (const std::string & name);
    Approximation less_lhs (const Approximation & lhs);
    Approximation less_rhs (const Approximation & rhs);
    Approximation nless_lhs (const Approximation & lhs);
    Approximation nless_rhs (const Approximation & rhs);

    Approximation lazy_fuse (std::vector<Approximation> & messages);
    Approximation lazy_injective_function_key (
        const std::string & name,
        const Approximation & key);
    Approximation lazy_injective_function_val (
        const std::string & name,
        const Approximation & val);
    Approximation lazy_binary_function_lhs_rhs (
        const std::string & name,
        const Approximation & lhs,
        const Approximation & rhs);
    Approximation lazy_binary_function_lhs_val (
        const std::string & name,
        const Approximation & lhs,
        const Approximation & val);
    Approximation lazy_binary_function_rhs_val (
        const std::string &,
        const Approximation & rhs,
        const Approximation & val);
    Approximation lazy_symmetric_function_lhs_rhs (
        const std::string & name,
        const Approximation & lhs,
        const Approximation & rhs);
    Approximation lazy_symmetric_function_lhs_val (
        const std::string & name,
        const Approximation & lhs,
        const Approximation & val);

private:

    Signature & signature () { return m_structure.signature(); }
    static uint64_t hash_name (const std::string & name);

    Trool lazy_disjoint (SetId lhs, SetId rhs);
    SetId lazy_fuse (
        const std::vector<Approximation> & messages,
        Parity parity);
    SetId lazy_find (const std::string & name, Parity parity);
    SetId lazy_find (
        const std::string & name,
        Parity parity,
        Direction direction,
        SetId arg);
    SetId lazy_find (
        const std::string & name,
        Parity parity,
        Direction direction,
        SetId arg0,
        SetId arg1);

    void lazy_close (Approximation & approx);

    SetId binary_function_lhs_rhs (
        const BinaryFunction & fun,
        SetId lhs,
        SetId rhs,
        Parity parity) const;
    SetId binary_function_lhs_val (
        const BinaryFunction & fun,
        SetId lhs,
        SetId val,
        Parity parity) const;
    SetId binary_function_rhs_val (
        const BinaryFunction & fun,
        SetId rhs,
        SetId val,
        Parity parity) const;

    // Structure parts.
    Structure & m_structure;
    const size_t m_item_dim;
    const Ob m_top;
    const Ob m_bot;
    const Ob m_identity;
    const BinaryRelation & m_less;
    const BinaryRelation & m_nless;
    const SymmetricFunction * const m_join;
    const SymmetricFunction * const m_rand;
    const InjectiveFunction * const m_quote;

    // DenseSet fingerprinting.
    DenseSetStore & m_sets;
    const SetId m_empty_set;
    std::vector<Approximation> m_known;
    Approximation m_maybe;
    Approximation m_truthy;
    Approximation m_falsey;
    Approximation m_unknown;

    // LazyMap caches.
    LazyMap<std::pair<SetId, SetId>, Trool, Trool::MAYBE,
            PodHash<std::pair<SetId, SetId>>>
        m_disjoint_cache;
    LazyMap<std::vector<SetId>, SetId, 0, VectorPodHash<SetId>> m_union_cache;
    // LazyMap<std::pair<SetId, SetId>, SetId> m_insn_cache; // TODO
    typedef std::tuple<uint64_t, Direction, Parity> CacheKey;
    std::unordered_map<uint64_t, Approximation> m_nullary_cache;
    std::unordered_map<
        CacheKey,
        std::unique_ptr<LazyMap<SetId, SetId>>,
        PodHash<CacheKey>> m_unary_cache;
    std::unordered_map<
        CacheKey,
        std::unique_ptr<LazyMap<std::pair<SetId, SetId>, SetId>>,
        PodHash<CacheKey>> m_binary_cache;
};

inline Approximation Approximator::interval (Ob lb, Ob ub) const
{
    POMAGMA_ASSERT1(not m_nless.find(lb, ub), "invalid interval");
    return {
        m_known[lb][BELOW],
        m_known[ub][ABOVE],
        m_known[ub][NBELOW],
        m_known[lb][NABOVE]
    };
}

inline Approximation Approximator::nullary_function (const std::string & name)
{
    auto i = m_nullary_cache.find(hash_name(name));
    POMAGMA_ASSERT(i != m_nullary_cache.end(),
        "unknown nullary function: " << name);
    return i->second;
}

inline Approximation Approximator::less_lhs (const Approximation & lhs)
{
    Approximation rhs = unknown();
    rhs[BELOW] = lhs[BELOW];
    rhs[NABOVE] = lhs[NABOVE];
    return rhs;
}

inline Approximation Approximator::less_rhs (const Approximation & rhs)
{
    Approximation lhs = unknown();
    lhs[ABOVE] = rhs[ABOVE];
    lhs[NBELOW] = rhs[NBELOW];
    return rhs;
}

inline Approximation Approximator::nless_lhs (const Approximation & lhs)
{
    Approximation rhs = unknown();
    rhs[NBELOW] = lhs[ABOVE];
    return rhs;
}

inline Approximation Approximator::nless_rhs (const Approximation & rhs)
{
    Approximation lhs = unknown();
    lhs[NABOVE] = rhs[BELOW];
    return rhs;
}

} // namespace intervals
} // namespace pomagma
