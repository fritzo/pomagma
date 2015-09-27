#pragma once

#include <pomagma/atlas/macro/structure_impl.hpp>
#include <pomagma/atlas/macro/util.hpp>
#include <pomagma/util/dense_set_store.hpp>
#include <pomagma/util/lazy_map.hpp>
#include <tuple>

// declared in pomagma/vendor/farmhash/farmhash.h
namespace util { uint64_t Fingerprint64(const char * s, size_t len); }

namespace pomagma {
namespace intervals {

enum Parity {ABOVE, BELOW, NABOVE, NBELOW};
enum Direction {VOID, KEY, VAL, LHS, RHS, LHS_RHS, LHS_VAL, RHS_VAL};
enum Arity {
    NULLARY_FUNCTION,
    INJECTIVE_FUNCTION,
    BINARY_FUNCTION,
    SYMMETRIC_FUNCTION
};

struct Approximation
{
    SetId sets[4];
    SetId & operator[] (Parity p) { return sets[p]; }
    SetId operator[] (Parity p) const { return sets[p]; }
};

class Approximator
{
public:

    Approximator (
            Structure & structure,
            DenseSetStore & sets,
            WorkerPool & worker_pool);

    Signature & signature () { return m_structure.signature(); }

    size_t test ();
    void validate (const Approximation & approx);
    bool refines (const Approximation & lhs, const Approximation & rhs) const;

    Approximation known (Ob ob) const;
    Approximation interval (Ob lb, Ob ub) const;
    Approximation unknown () const { return interval(m_bot, m_top); }
    Approximation truthy () const { return known(m_identity); }
    Approximation falsey () const { return known(m_bot); }
    Approximation maybe () const { return interval(m_bot, m_identity); }

    SetId lazy_union (const Approximation & lhs, SetId rhs);
    SetId lazy_nullary_function (const std::string & name, Parity parity);
    SetId lazy_unary_function_key (
        const std::string & name,
        Parity parity,
        SetId key);
    SetId lazy_unary_function_val (
        const std::string & name,
        Parity parity,
        SetId val);
    SetId lazy_binary_function_lhs_rhs (
        const std::string & name,
        Parity parity,
        SetId lhs,
        SetId rhs);
    SetId lazy_binary_function_lhs_val (
        const std::string & name,
        Parity parity,
        SetId rhs,
        SetId val);
    SetId lazy_binary_function_rhs_val (
        const std::string &,
        Parity parity,
        SetId rhs,
        SetId val);

private:

    static uint64_t hash_name (const string & name);
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
    std::vector<SetId> m_known[4];

    // LazyMap caches.
    typedef std::tuple<uint64_t, Parity, Direction> CacheKey;
    std::unordered_map<CacheKey, SetId> m_nullary_cache;
    std::unordered_map<CacheKey, std::unique_ptr<LazyMap<SetId, SetId>>>
        m_unary_cache;
    std::unordered_map<
        CacheKey,
        std::unique_ptr<LazyMap<std::pair<SetId, SetId>, SetId>>>
        m_binary_cache;
};

inline Approximation Approximator::known (Ob ob) const
{
    return {
        m_known[BELOW][ob],
        m_known[ABOVE][ob],
        m_known[NBELOW][ob],
        m_known[NABOVE][ob]
    };
}

inline Approximation Approximator::interval (Ob lb, Ob ub) const
{
    POMAGMA_ASSERT1(not m_nless.find(lb, ub), "invalid interval");
    return {
        m_known[BELOW][lb],
        m_known[ABOVE][ub],
        m_known[NBELOW][ub],
        m_known[NABOVE][lb]
    };
}

inline SetId Approximator::lazy_union (SetId lhs, SetId rhs)
{
    if (lhs == rhs) { return lhs; }
    if (lhs > rhs) { std::swap(lhs, rhs); }
    return m_union_cache.try_find({lhs, rhs});
}

inline uint64_t Approximator::hash_name (const string & name)
{
    return util::Fingerprint64(name.data(), name.size());
}

inline SetId Approximator::lazy_find (const std::string & name, Parity parity)
{
    auto i = m_nullary_cache.find({hash_name(name), parity, direction});
    POMAGMA_ASSERT1(i != m_nullary_cache.end(), "programmer error");
    return i->second;
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

SetId Approximator::lazy_nullary_function (const std::string & name, Parity parity)
{
    return try_find(name, parity);
}

SetId Approximator::lazy_binary_function_lhs_rhs (
    const std::string & name,
    Parity parity,
    SetId lhs,
    SetId rhs)
{
    return try_find(name, parity, LHS_RHS, lhs, rhs);
}

} // namespace intervals
} // namespace pomagma
