#include "sampler.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"

#define POMAGMA_DEBUG1(message)
//#define POMAGMA_DEBUG1(message) POMAGMA_DEBUG(message)

namespace pomagma
{

//----------------------------------------------------------------------------
// construction

Sampler::Sampler (Carrier & carrier)
    : m_carrier(carrier)
{
}

template<class Function>
inline void validate_function_probs (
        const std::unordered_map<std::string, const Function *> & funs,
        const std::unordered_map<const Function *, float> & probs)
{
    for (const auto & ifun : funs) {
        auto iprob = probs.find(ifun.second);
        POMAGMA_ASSERT(iprob != probs.end(), "is missing " << ifun.first);
        float prob = iprob->second;
        POMAGMA_ASSERT(prob >= 0,
                "P(" << ifun.first << ") = " << iprob->second);
    }
}

void Sampler::validate () const
{
    POMAGMA_INFO("Validating Sampler");

    float total =
        m_nullary_prob +
        m_injective_prob +
        m_binary_prob +
        m_symmetric_prob;

    float tol = 1e-6;
    POMAGMA_ASSERT_LE(total, 1 + tol);
    POMAGMA_ASSERT_LE(1 - tol, total);

    validate_function_probs(m_nullary_funs, m_nullary_probs);
    validate_function_probs(m_injective_funs, m_injective_probs);
    validate_function_probs(m_binary_funs, m_binary_probs);
    validate_function_probs(m_symmetric_funs, m_symmetric_probs);

    // these are required for the implementation of sampling below
    POMAGMA_ASSERT_LT(0, m_nullary_prob);
    POMAGMA_ASSERT_LT(0, m_binary_prob);
}

template<class T>
inline float sum (const std::unordered_map<T, float> & map)
{
    float result = 0;
    for (auto & pair : map) {
        result += pair.second;
    }
    return result;
}

template<class Key>
inline Key sample (
        const std::unordered_map<Key, float> & probs,
        float total)
{
    while (true) {
        float r = random_01() * total;
        for (const auto & pair : probs) {
            Key key = pair.first;
            float prob = pair.second;
            if ((r -= prob) < 0) {
                return key;
            }
        }
        // occasionally fall through due to rounding error
    }
}

void Sampler::declare (const std::string & name, const NullaryFunction & fun)
{
    m_nullary_funs[name] = & fun;
    set_prob(& fun, 0);
}

void Sampler::declare (const std::string & name, const InjectiveFunction & fun)
{
    m_injective_funs[name] = & fun;
    set_prob(& fun, 0);
}

void Sampler::declare (const std::string & name, const BinaryFunction & fun)
{
    m_binary_funs[name] = & fun;
    set_prob(& fun, 0);
}

void Sampler::declare (const std::string & name, const SymmetricFunction & fun)
{
    m_symmetric_funs[name] = & fun;
    set_prob(& fun, 0);
}

inline void Sampler::set_prob (const NullaryFunction * fun, float prob)
{
    m_nullary_probs[fun] = prob;
    m_nullary_prob = sum(m_nullary_probs);
}

inline void Sampler::set_prob (const InjectiveFunction * fun, float prob)
{
    m_injective_probs[fun] = prob;
    m_injective_prob = sum(m_injective_probs);
}

inline void Sampler::set_prob (const BinaryFunction * fun, float prob)
{
    m_binary_probs[fun] = prob;
    m_binary_prob = sum(m_binary_probs);
}

inline void Sampler::set_prob (const SymmetricFunction * fun, float prob)
{
    m_symmetric_probs[fun] = prob;
    m_symmetric_prob = sum(m_symmetric_probs);
}

template<class Function>
inline bool Sampler::try_set_prob_ (
        const std::unordered_map<std::string, const Function *> & funs,
        const std::string & name,
        float prob)
{
    auto iter = funs.find(name);
    if (iter == funs.end()) {
        return false;
    } else {
        set_prob(iter->second, prob);
        return true;
    }
}

void Sampler::set_prob (const std::string & name, float prob)
{
    bool found =
        try_set_prob_(m_nullary_funs, name, prob) or
        try_set_prob_(m_injective_funs, name, prob) or
        try_set_prob_(m_binary_funs, name, prob) or
        try_set_prob_(m_symmetric_funs, name, prob);
    POMAGMA_ASSERT(found, "failed to set prob of function: " << name);
    m_bounded_samplers.clear();
}

//----------------------------------------------------------------------------
// sampling

// base case
Sampler::BoundedSampler::BoundedSampler (
        const Sampler & sampler)
    : injective(0),
      binary(0),
      symmetric(0),
      total(sampler.m_nullary_prob),
      compound_injective(0),
      compound_binary(0),
      compound_symmetric(0),
      compound_total(0)
{
}

// induction step
Sampler::BoundedSampler::BoundedSampler (
        const Sampler & sampler,
        const BoundedSampler & prev)
    : injective(sampler.m_injective_prob * prev.total),
      binary(sampler.m_binary_prob * (prev.total * prev.total)),
      symmetric(sampler.m_symmetric_prob * (prev.total * prev.total)),
      total(sampler.m_nullary_prob + injective + binary + symmetric),
      compound_injective(sampler.m_injective_prob),
      compound_binary(sampler.m_binary_prob * prev.total),
      compound_symmetric(sampler.m_symmetric_prob * prev.total),
      compound_total(compound_injective +
                     compound_binary +
                     compound_symmetric)
{
}

inline Sampler::Arity Sampler::BoundedSampler::sample_arity () const
{
    POMAGMA_ASSERT3(total > 0, "zero probability mass");
    POMAGMA_ASSERT4(total > injective + binary + symmetric,
            "implementation assumes P(nullary) > 0");

    float r = random_01() * total;
    if (binary and (r -= binary) < 0) return BINARY;
    if (symmetric and (r -= symmetric) < 0) return SYMMETRIC;
    if (injective and (r -= injective) < 0) return INJECTIVE;
    return NULLARY;
}

inline Sampler::Arity Sampler::BoundedSampler::sample_compound_arity () const
{
    POMAGMA_ASSERT3(compound_total > 0, "zero probability mass");
    POMAGMA_ASSERT4(compound_binary > 0,
            "implementation assumes P(compound_binary) > 0");

    float r = random_01() * compound_total;
    if (symmetric and (r -= compound_symmetric) < 0) return SYMMETRIC;
    if (injective and (r -= compound_injective) < 0) return INJECTIVE;
    return BINARY;
}

inline const Sampler::BoundedSampler & Sampler::bounded_sampler (
        size_t max_depth) const
{
    while (unlikely(max_depth >= m_bounded_samplers.size())) {
        if (unlikely(m_bounded_samplers.empty())) {
            m_bounded_samplers.push_back(BoundedSampler(*this));
        } else {
            m_bounded_samplers.push_back(
                    BoundedSampler(*this, m_bounded_samplers.back()));
        }
    }

    return m_bounded_samplers[max_depth];
}

Ob Sampler::try_insert_random () const
{
    try {
        Ob ob = insert_random_nullary();
        for (size_t depth = 1; depth; ++depth) {
            POMAGMA_DEBUG1("sampling at depth " << depth);
            ob = insert_random_compound(ob, depth);
        }
    } catch (InsertException e) {
        return e.inserted;
    }

    POMAGMA_ERROR("sampler failed");
    return 0;
}

static const char * g_arity_names[] __attribute__((unused)) =
{
    "NULLARY",
    "INJECTIVE",
    "BINARY",
    "SYMMETRIC"
};

inline Ob Sampler::insert_random_compound (Ob ob, size_t max_depth) const
{
    POMAGMA_ASSERT3(max_depth > 0, "cannot make compound with max_depth 0");
    const BoundedSampler & sampler = bounded_sampler(max_depth);
    Arity arity = sampler.sample_compound_arity();
    POMAGMA_DEBUG1("compound_arity = " << g_arity_names[arity]);
    switch (arity) {
        case NULLARY: {
            POMAGMA_ERROR("unreachable");
        } break;

        case INJECTIVE: {
            return insert_random_injective(ob);
        } break;

        case BINARY: {
            Ob other = insert_random(max_depth - 1);
            if (random_bool(0.5)) std::swap(ob, other);
            return insert_random_binary(ob, other);
        } break;

        case SYMMETRIC: {
            Ob other = insert_random(max_depth - 1);
            return insert_random_symmetric(ob, other);
        } break;
    }

    POMAGMA_ERROR("unreachable");
    return 0;
}

inline Ob Sampler::insert_random (size_t max_depth) const
{
    const BoundedSampler & sampler = bounded_sampler(max_depth);
    Arity arity = sampler.sample_arity();
    POMAGMA_DEBUG1("arity = " << g_arity_names[arity]);
    switch (arity) {
        case NULLARY: {
            return insert_random_nullary();
        } break;

        case INJECTIVE: {
            POMAGMA_ASSERT3(max_depth > 0, "max_depth bottomed-out");
            Ob key = insert_random(max_depth - 1);
            return insert_random_injective(key);
        } break;

        case BINARY: {
            POMAGMA_ASSERT3(max_depth > 0, "max_depth bottomed-out");
            Ob lhs = insert_random(max_depth - 1);
            Ob rhs = insert_random(max_depth - 1);
            return insert_random_binary(lhs, rhs);
        } break;

        case SYMMETRIC: {
            POMAGMA_ASSERT3(max_depth > 0, "max_depth bottomed-out");
            Ob lhs = insert_random(max_depth - 1);
            Ob rhs = insert_random(max_depth - 1);
            return insert_random_symmetric(lhs, rhs);
        } break;
    }

    POMAGMA_ERROR("unreachable");
    return 0;
}

inline Ob Sampler::insert_random_nullary () const
{
    auto & fun = * sample(m_nullary_probs, m_nullary_prob);
    if (Ob val = fun.find()) {
        return m_carrier.find(val);
    } else {
        if (Ob val = m_carrier.try_insert()) {
            fun.insert(val);
            throw(InsertException(val));
        } else {
            throw(InsertException(0));
        }
    }
}

inline Ob Sampler::insert_random_injective (Ob key) const
{
    auto & fun = * sample(m_injective_probs, m_injective_prob);
    if (Ob val = fun.find(key)) {
        return m_carrier.find(val);
    } else {
        if (Ob val = m_carrier.try_insert()) {
            fun.insert(key, val);
            throw(InsertException(val));
        } else {
            throw(InsertException(0));
        }
    }
}

inline Ob Sampler::insert_random_binary (Ob lhs, Ob rhs) const
{
    auto & fun = * sample(m_binary_probs, m_binary_prob);
    if (Ob val = fun.find(lhs, rhs)) {
        return m_carrier.find(val);
    } else {
        if (Ob val = m_carrier.try_insert()) {
            fun.insert(lhs, rhs, val);
            throw(InsertException(val));
        } else {
            throw(InsertException(0));
        }
    }
}

inline Ob Sampler::insert_random_symmetric (Ob lhs, Ob rhs) const
{
    auto & fun = * sample(m_symmetric_probs, m_symmetric_prob);
    if (Ob val = fun.find(lhs, rhs)) {
        return m_carrier.find(val);
    } else {
        if (Ob val = m_carrier.try_insert()) {
            fun.insert(lhs, rhs, val);
            throw(InsertException(val));
        } else {
            throw(InsertException(0));
        }
    }
}

} // namespace pomagma
