#pragma once

#include "sampler.hpp"
#include <pomagma/language/language.pb.h>

namespace pomagma
{

//----------------------------------------------------------------------------
// Construction

Sampler::Sampler (Signature & signature)
    : m_signature(signature),
      m_sample_count(0),
      m_reject_count(0),
      m_arity_sample_count(0),
      m_compound_arity_sample_count(0)
{
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

    // these are required for the implementation of sampling below
    POMAGMA_ASSERT_LT(0, m_nullary_prob);
    POMAGMA_ASSERT_LT(0, m_binary_prob);
}

void Sampler::log_stats () const
{
    const Sampler & sampler = * this;
    POMAGMA_PRINT(sampler.m_sample_count.load());
    POMAGMA_PRINT(sampler.m_reject_count.load());
    POMAGMA_PRINT(sampler.m_arity_sample_count.load());
    POMAGMA_PRINT(sampler.m_compound_arity_sample_count.load());
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
        float total,
        rng_t & rng)
{
    std::uniform_real_distribution<float> random_point(0, total);
    while (true) {
        float r = random_point(rng);
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
        const std::unordered_map<std::string, Function *> & funs,
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
        try_set_prob_(m_signature.nullary_functions(), name, prob) or
        try_set_prob_(m_signature.injective_functions(), name, prob) or
        try_set_prob_(m_signature.binary_functions(), name, prob) or
        try_set_prob_(m_signature.symmetric_functions(), name, prob);
    POMAGMA_ASSERT(found, "failed to set prob of function: " << name);
    m_bounded_samplers.clear();
}

void Sampler::load (const std::string & language_file)
{
    POMAGMA_INFO("Loading language");

    messaging::Language language;

    std::ifstream file(language_file, std::ios::in | std::ios::binary);
    POMAGMA_ASSERT(file.is_open(),
        "failed to open language file " << language_file);
    POMAGMA_ASSERT(language.ParseFromIstream(&file),
        "failed tp parse language file " << language_file);

    for (int i = 0; i < language.terms_size(); ++i) {
        const auto & term = language.terms(i);
        POMAGMA_DEBUG("setting P(" << term.name() << ") = " << term.weight());
        set_prob(term.name(), term.weight());
    }
}

//----------------------------------------------------------------------------
// Sampling

// unused
Sampler::BoundedSampler::BoundedSampler ()
    : injective(0),
      binary(0),
      symmetric(0),
      total(0),
      compound_injective(0),
      compound_binary(0),
      compound_symmetric(0),
      compound_total(0)
{
    POMAGMA_ERROR("unused");
}

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

inline Sampler::Arity Sampler::BoundedSampler::sample_arity (rng_t & rng) const
{
    POMAGMA_ASSERT3(total > 0, "zero probability mass");
    POMAGMA_ASSERT4(total > injective + binary + symmetric,
            "implementation assumes P(nullary) > 0");

    std::uniform_real_distribution<float> random_point(0, total);
    float r = random_point(rng);
    // FIXME valgrind complains about the following lines,
    // "Conditional jump or move depends on uninitialised value(s)"
    if (binary and (r -= binary) < 0) return BINARY;
    if (symmetric and (r -= symmetric) < 0) return SYMMETRIC;
    if (injective and (r -= injective) < 0) return INJECTIVE;
    return NULLARY;
}

inline Sampler::Arity Sampler::BoundedSampler::sample_compound_arity (
        rng_t & rng) const
{
    POMAGMA_ASSERT3(compound_total > 0, "zero probability mass");
    POMAGMA_ASSERT4(compound_binary > 0,
            "implementation assumes P(compound_binary) > 0");

    std::uniform_real_distribution<float> random_point(0, compound_total);
    float r = random_point(rng);
    // FIXME valgrind complains about the following lines,
    // "Conditional jump or move depends on uninitialised value(s)"
    if (symmetric and (r -= compound_symmetric) < 0) return SYMMETRIC;
    if (injective and (r -= compound_injective) < 0) return INJECTIVE;
    return BINARY;
}

inline const Sampler::BoundedSampler & Sampler::bounded_sampler (
        size_t max_depth) const
{
    // this may safely overgrow the cache by (thread_count - 1) items
    while (true) {
        {
            SharedMutex::SharedLock lock(m_bounded_samplers_mutex);
            if (likely(max_depth < m_bounded_samplers.size())) {
                // use cached value
                return m_bounded_samplers[max_depth];
            }
        }
        {
            // grow cache
            SharedMutex::UniqueLock lock(m_bounded_samplers_mutex);
            if (unlikely(m_bounded_samplers.empty())) {
                m_bounded_samplers.push_back(BoundedSampler(*this));
            } else {
                m_bounded_samplers.push_back(
                        BoundedSampler(*this, m_bounded_samplers.back()));
            }
        }
    }
}

Ob Sampler::try_insert_random (rng_t & rng, Policy & policy) const
{
    while (true) {
        try {
            Ob ob = insert_random_nullary(rng, policy);
            for (size_t depth = 1; depth; ++depth) {
                //POMAGMA_DEBUG1("sampling at depth " << depth);
                ob = insert_random_compound(ob, depth, rng, policy);
            }
        } catch (ObInsertedException e) {
            m_sample_count += 1;
            return e.inserted;
        } catch (ObRejectedException) {
            m_reject_count += 1;
            continue;
        } catch (InsertionFailedException e) {
            return 0;
        }
        POMAGMA_ERROR("unreachable");
    }

    return 0;
}

static const char * g_sampler_arity_names[] __attribute__((unused)) =
{
    "NULLARY",
    "INJECTIVE",
    "BINARY",
    "SYMMETRIC"
};

inline Ob Sampler::insert_random_compound (
        Ob ob,
        size_t max_depth,
        rng_t & rng,
        Policy & policy) const
{
    POMAGMA_ASSERT3(max_depth > 0, "cannot make compound with max_depth 0");
    const BoundedSampler & sampler = bounded_sampler(max_depth);
    Arity arity = sampler.sample_compound_arity(rng);
    m_compound_arity_sample_count += 1;
    //POMAGMA_DEBUG1("compound_arity = " << g_sampler_arity_names[arity]);
    switch (arity) {
        case NULLARY: {
            POMAGMA_ERROR("unreachable");
        } break;

        case INJECTIVE: {
            return insert_random_injective(ob, rng, policy);
        } break;

        case BINARY: {
            Ob other = insert_random(max_depth - 1, rng, policy);
            std::bernoulli_distribution randomly_swap(0.5);
            if (randomly_swap(rng)) std::swap(ob, other);
            return insert_random_binary(ob, other, rng, policy);
        } break;

        case SYMMETRIC: {
            Ob other = insert_random(max_depth - 1, rng, policy);
            return insert_random_symmetric(ob, other, rng, policy);
        } break;
    }

    POMAGMA_ERROR("unreachable");
    return 0;
}

inline Ob Sampler::insert_random (
        size_t max_depth,
        rng_t & rng,
        Policy & policy) const
{
    const BoundedSampler & sampler = bounded_sampler(max_depth);
    Arity arity = sampler.sample_arity(rng);
    m_arity_sample_count += 1;
    //POMAGMA_DEBUG1("arity = " << g_sampler_arity_names[arity]);
    switch (arity) {
        case NULLARY: {
            return insert_random_nullary(rng, policy);
        } break;

        case INJECTIVE: {
            POMAGMA_ASSERT3(max_depth > 0, "max_depth bottomed-out");
            Ob key = insert_random(max_depth - 1, rng, policy);
            return insert_random_injective(key, rng, policy);
        } break;

        case BINARY: {
            POMAGMA_ASSERT3(max_depth > 0, "max_depth bottomed-out");
            Ob lhs = insert_random(max_depth - 1, rng, policy);
            Ob rhs = insert_random(max_depth - 1, rng, policy);
            return insert_random_binary(lhs, rhs, rng, policy);
        } break;

        case SYMMETRIC: {
            POMAGMA_ASSERT3(max_depth > 0, "max_depth bottomed-out");
            Ob lhs = insert_random(max_depth - 1, rng, policy);
            Ob rhs = insert_random(max_depth - 1, rng, policy);
            return insert_random_symmetric(lhs, rhs, rng, policy);
        } break;
    }

    POMAGMA_ERROR("unreachable");
    return 0;
}

inline Ob Sampler::insert_random_nullary (
        rng_t & rng,
        Policy & policy) const
{
    auto & fun = * sample(m_nullary_probs, m_nullary_prob, rng);
    return policy.sample(fun);
}

inline Ob Sampler::insert_random_injective (
        Ob key,
        rng_t & rng,
        Policy & policy) const
{
    auto & fun = * sample(m_injective_probs, m_injective_prob, rng);
    return policy.sample(fun, key);
}

inline Ob Sampler::insert_random_binary (
        Ob lhs,
        Ob rhs,
        rng_t & rng,
        Policy & policy) const
{
    auto & fun = * sample(m_binary_probs, m_binary_prob, rng);
    return policy.sample(fun, lhs, rhs);
}

inline Ob Sampler::insert_random_symmetric (
        Ob lhs,
        Ob rhs,
        rng_t & rng,
        Policy & policy) const
{
    auto & fun = * sample(m_symmetric_probs, m_symmetric_prob, rng);
    return policy.sample(fun, lhs, rhs);
}

} // namespace pomagma
