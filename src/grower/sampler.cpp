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

Sampler::Sampler (Signature & signature)
    : m_signature(signature),
      m_sample_count(0),
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

inline Sampler::Arity Sampler::BoundedSampler::sample_arity (rng_t & rng) const
{
    POMAGMA_ASSERT3(total > 0, "zero probability mass");
    POMAGMA_ASSERT4(total > injective + binary + symmetric,
            "implementation assumes P(nullary) > 0");

    std::uniform_real_distribution<float> random_point(0, total);
    float r = random_point(rng);
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

Ob Sampler::try_insert_random (rng_t & rng) const
{
    try {
        Ob ob = insert_random_nullary(rng);
        for (size_t depth = 1; depth; ++depth) {
            POMAGMA_DEBUG1("sampling at depth " << depth);
            ob = insert_random_compound(ob, depth, rng);
        }
    } catch (InsertException e) {
        if (e.inserted) {
            m_sample_count.fetch_add(1, relaxed);
        }
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

inline Ob Sampler::insert_random_compound (
        Ob ob,
        size_t max_depth,
        rng_t & rng) const
{
    POMAGMA_ASSERT3(max_depth > 0, "cannot make compound with max_depth 0");
    const BoundedSampler & sampler = bounded_sampler(max_depth);
    Arity arity = sampler.sample_compound_arity(rng);
    m_compound_arity_sample_count.fetch_add(1, relaxed);
    POMAGMA_DEBUG1("compound_arity = " << g_arity_names[arity]);
    switch (arity) {
        case NULLARY: {
            POMAGMA_ERROR("unreachable");
        } break;

        case INJECTIVE: {
            return insert_random_injective(ob, rng);
        } break;

        case BINARY: {
            Ob other = insert_random(max_depth - 1, rng);
            std::bernoulli_distribution randomly_swap(0.5);
            if (randomly_swap(rng)) std::swap(ob, other);
            return insert_random_binary(ob, other, rng);
        } break;

        case SYMMETRIC: {
            Ob other = insert_random(max_depth - 1, rng);
            return insert_random_symmetric(ob, other, rng);
        } break;
    }

    POMAGMA_ERROR("unreachable");
    return 0;
}

inline Ob Sampler::insert_random (size_t max_depth, rng_t & rng) const
{
    const BoundedSampler & sampler = bounded_sampler(max_depth);
    Arity arity = sampler.sample_arity(rng);
    m_arity_sample_count.fetch_add(1, relaxed);
    POMAGMA_DEBUG1("arity = " << g_arity_names[arity]);
    switch (arity) {
        case NULLARY: {
            return insert_random_nullary(rng);
        } break;

        case INJECTIVE: {
            POMAGMA_ASSERT3(max_depth > 0, "max_depth bottomed-out");
            Ob key = insert_random(max_depth - 1, rng);
            return insert_random_injective(key, rng);
        } break;

        case BINARY: {
            POMAGMA_ASSERT3(max_depth > 0, "max_depth bottomed-out");
            Ob lhs = insert_random(max_depth - 1, rng);
            Ob rhs = insert_random(max_depth - 1, rng);
            return insert_random_binary(lhs, rhs, rng);
        } break;

        case SYMMETRIC: {
            POMAGMA_ASSERT3(max_depth > 0, "max_depth bottomed-out");
            Ob lhs = insert_random(max_depth - 1, rng);
            Ob rhs = insert_random(max_depth - 1, rng);
            return insert_random_symmetric(lhs, rhs, rng);
        } break;
    }

    POMAGMA_ERROR("unreachable");
    return 0;
}

inline Ob Sampler::insert_random_nullary (rng_t & rng) const
{
    auto & fun = * sample(m_nullary_probs, m_nullary_prob, rng);
    if (Ob val = fun.find()) {
        return carrier().find(val);
    } else {
        if (Ob val = carrier().try_insert()) {
            fun.insert(val);
            throw(InsertException(val));
        } else {
            throw(InsertException(0));
        }
    }
}

inline Ob Sampler::insert_random_injective (Ob key, rng_t & rng) const
{
    auto & fun = * sample(m_injective_probs, m_injective_prob, rng);
    if (Ob val = fun.find(key)) {
        return carrier().find(val);
    } else {
        if (Ob val = carrier().try_insert()) {
            fun.insert(key, val);
            throw(InsertException(val));
        } else {
            throw(InsertException(0));
        }
    }
}

inline Ob Sampler::insert_random_binary (Ob lhs, Ob rhs, rng_t & rng) const
{
    auto & fun = * sample(m_binary_probs, m_binary_prob, rng);
    if (Ob val = fun.find(lhs, rhs)) {
        return carrier().find(val);
    } else {
        if (Ob val = carrier().try_insert()) {
            fun.insert(lhs, rhs, val);
            throw(InsertException(val));
        } else {
            throw(InsertException(0));
        }
    }
}

inline Ob Sampler::insert_random_symmetric (Ob lhs, Ob rhs, rng_t & rng) const
{
    auto & fun = * sample(m_symmetric_probs, m_symmetric_prob, rng);
    if (Ob val = fun.find(lhs, rhs)) {
        return carrier().find(val);
    } else {
        if (Ob val = carrier().try_insert()) {
            fun.insert(lhs, rhs, val);
            throw(InsertException(val));
        } else {
            throw(InsertException(0));
        }
    }
}

//----------------------------------------------------------------------------
// parsing

Ob Sampler::try_insert (const std::string & expression) const
{
    std::stringstream stream(expression);
    return try_insert(stream);
}

Ob Sampler::try_insert (std::stringstream & stream) const
{
    std::string token;
    POMAGMA_ASSERT(std::getline(stream, token, ' '),
            "expression terminated prematurely");

    if (const auto * fun = m_signature.nullary_functions(token)) {
        return try_insert(fun);
    } else if (const auto * fun = m_signature.injective_functions(token)) {
        if (Ob key = try_insert(stream)) {
            return try_insert(fun, key);
        }
    } else if (const auto * fun = m_signature.binary_functions(token)) {
        if (Ob lhs = try_insert(stream)) {
            if (Ob rhs = try_insert(stream)) {
                return try_insert(fun, lhs, rhs);
            }
        }
    } else if (const auto * fun = m_signature.symmetric_functions(token)) {
        if (Ob lhs = try_insert(stream)) {
            if (Ob rhs = try_insert(stream)) {
                return try_insert(fun, lhs, rhs);
            }
        }
    } else {
        POMAGMA_ERROR("bad token: " << token);
    }
    return 0;
}

inline Ob Sampler::try_insert (const NullaryFunction * fun) const
{
    if (Ob val = fun->find()) {
        return val;
    } else if (Ob val = carrier().try_insert()) {
        fun->insert(val);
        return val;
    } else {
        return 0;
    }
}

inline Ob Sampler::try_insert (const InjectiveFunction * fun, Ob key) const
{
    if (Ob val = fun->find(key)) {
        return val;
    } else if (Ob val = carrier().try_insert()) {
        fun->insert(key, val);
        return val;
    } else {
        return 0;
    }
}

inline Ob Sampler::try_insert (const BinaryFunction * fun, Ob lhs, Ob rhs) const
{
    if (Ob val = fun->find(lhs, rhs)) {
        return val;
    } else if (Ob val = carrier().try_insert()) {
        fun->insert(lhs, rhs, val);
        return val;
    } else {
        return 0;
    }
}

inline Ob Sampler::try_insert (
        const SymmetricFunction * fun,
        Ob lhs,
        Ob rhs) const
{
    if (Ob val = fun->find(lhs, rhs)) {
        return val;
    } else if (Ob val = carrier().try_insert()) {
        fun->insert(lhs, rhs, val);
        return val;
    } else {
        return 0;
    }
}

} // namespace pomagma
