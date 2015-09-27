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
    SetId bounds[4];
    // Ob ob; // TODO
    // bool satisfiable; // TODO

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

    size_t test ();
    void validate (const Approximation & approx);

    bool is_valid (const Approximation & approx);
    bool refines (const Approximation & lhs, const Approximation & rhs) const;

    Approximation pending () const { return {0, 0, 0, 0}; }
    Approximation known (Ob ob) const;
    Approximation interval (Ob lb, Ob ub) const;
    Approximation unknown () const { return m_unknown; }
    Approximation truthy () const { return known(m_identity); }
    Approximation falsey () const { return known(m_bot); }
    Approximation maybe () const { return interval(m_bot, m_identity); }
    Approximation nullary_function (const std::string & name);
    Approximation less_lhs (const Approximation & lhs);
    Approximation less_rhs (const Approximation & rhs);
    Approximation nless_lhs (const Approximation & lhs);
    Approximation nless_rhs (const Approximation & rhs);
    Approximation unary_relation (
        const std::string & name,
        const Approximation & key);
    Approximation binary_relation (
        const std::string & name,
        const Approximation & lhs,
        const Approximation & rhs);

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
    static uint64_t hash_name (const string & name);

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
    Approximation m_unknown;

    // LazyMap caches.
    struct VectorSetIdHash
    {
        uint64_t operator() (const std::vector<SetId> & x) const
        {
            return util::Fingerprint64(
                reinterpret_cast<const char *>(x.data()),
                x.size() * sizeof(SetId));
        }
    };
    LazyMap<std::vector<SetId>, SetId, 0, VectorSetIdHash> m_fuse_cache;
    typedef std::tuple<uint64_t, Parity, Direction> CacheKey;
    std::unordered_map<uint64_t, Approximation> m_nullary_cache;
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

inline Approximation Approximator::nullary_function (const std::string & name)
{
    auto i = m_nullary_cache.find(hash_name(name));
    POMAGMA_ASSERT(i != m_nullary_cache.end(), "programmer error");
    return i->second;
}

inline Approximation Approximator::unary_relation (
    const std::string & name,
    const Approximation & key)
{
#if 0 // TODO add a .ob field to Approximation
    if (key.ob) {
        if (m_structure.unary_relation(name).find(key.ob)) {
            return truthy();
        }
        const string negated = signature.negate(name);
        if (const auto * rel = signature.unary_relation(name)) {
            if (rel->find(key.ob)) {
                return falsey();
            }
        }
    }
#endif // TODO
    return maybe();
}

inline Approximation Approximator::binary_relation (
    const std::string & name,
    const Approximation & lhs,
    const Approximation & rhs)
{
#if 0 // TODO add a .ob field to Approximation
    if (lhs.ob and rhs.ob) {
        if (m_structure.binary_relation(name).find(lhs.ob, rhs.ob)) {
            return truthy();
        }
        const string negated = signature.negate(name);
        if (const auto * rel = signature.binary_relation(name)) {
            if (rel->find(lhs.ob, rhs.ob)) {
                return falsey();
            }
        }
    }
#endif // TODO
    return maybe();
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
