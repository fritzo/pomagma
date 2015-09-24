#pragma once

#include <pomagma/atlas/macro/structure_impl.hpp>
#include <pomagma/atlas/macro/util.hpp>
#include <pomagma/util/dense_set_store.hpp>
#include <pomagma/util/lazy_map.hpp>

// declared in pomagma/vendor/farmhash/farmhash.h
namespace util {
uint64_t Fingerprint64(const char* s, size_t len);
} // namespace util

namespace pomagma {
namespace intervals {

struct Approximation
{
    SetId below;
    SetId above;
    SetId nbelow;
    SetId nabove;
};

class Approximator
{
public:

    struct Term
    {
        enum Parity { ABOVE, BELOW, NABOVE, NBELOW };
        enum Arity {
            NULLARY_FUNCTION,
            INJECTIVE_FUNCTION,
            BINARY_FUNCTION,
            SYMMETRIC_FUNCTION,
            UNARY_RELATION,
            BINARY_RELATION
        };

        bool operator== (const Term & other) const
        {
            return not operator!=(other);
        }
        bool operator!= (const Term & other) const
        {
            return memcmp(this, & other, sizeof(Term));
        }
        struct Hash
        {
            uint64_t operator() (const Term & x) const
            {
                return util::Fingerprint64(
                    reinterpret_cast<const char *>(& x), sizeof(x));
            }
        };

        Parity parity;
        Arity arity;
        uint64_t name_hash;
        SetId args[2];
    };

    Approximator (Structure & structure, DenseSetStore & sets);

    Signature & signature () { return m_structure.signature(); }

    size_t test ();
    void validate (const Approximation & approx);

    Approximation known (Ob ob) const
    {
        return {m_below[ob], m_above[ob], m_nbelow[ob], m_nabove[ob]};
    }
    Approximation interval (Ob lb, Ob ub) const
    {
        POMAGMA_ASSERT1(not m_nless.find(lb, ub), "invalid interval");
        return {m_below[lb], m_above[ub], m_nbelow[ub], m_nabove[lb]};
    }
    Approximation unknown () const { return interval(m_bot, m_top); }
    Approximation truthy () const { return known(m_identity); }
    Approximation falsey () const { return known(m_bot); }
    Approximation maybe () const { return interval(m_bot, m_identity); }

    SetId try_find (const Term & term) { return m_cache.try_find(term); }

private:

    SetId compute (const Term & term);

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

    DenseSetStore & m_sets;
    std::vector<SetId> m_below;
    std::vector<SetId> m_above;
    std::vector<SetId> m_nbelow;
    std::vector<SetId> m_nabove;
    LazyMap<Term, SetId, 0, Term::Hash> m_cache;
};

} // namespace intervals
} // namespace pomagma
