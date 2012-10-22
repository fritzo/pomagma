#include "sampler.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"

namespace pomagma
{

//----------------------------------------------------------------------------
// construction

Sampler::Sampler (Carrier & carrier)
    : m_carrier(carrier)
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

    for (auto & pair : m_nullary_funs) {
        float prob = m_nullary_probs.find(pair.second)->second;
        POMAGMA_ASSERT_LT(0, prob);
    }
    for (auto & pair : m_injective_funs) {
        float prob = m_injective_probs.find(pair.second)->second;
        POMAGMA_ASSERT_LT(0, prob);
    }
    for (auto & pair : m_binary_funs) {
        float prob = m_binary_probs.find(pair.second)->second;
        POMAGMA_ASSERT_LT(0, prob);
    }
    for (auto & pair : m_symmetric_funs) {
        float prob = m_symmetric_probs.find(pair.second)->second;
        POMAGMA_ASSERT_LT(0, prob);
    }
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

inline Sampler::Arity Sampler::BoundedSampler::sample_arity () const
{
    while (true) {
        float r = random_01() * total;
        if ((r -= nullary) < 0) return NULLARY;
        if ((r -= injective) < 0) return INJECTIVE;
        if ((r -= binary) < 0) return BINARY;
        if ((r -= symmetric) < 0) return SYMMETRIC;
        // occasionally fall through due to rounding error
    }
}

inline Sampler::Arity Sampler::BoundedSampler::sample_compound_arity () const
{
    while (true) {
        float r = random_01() * (total - nullary);
        if ((r -= injective) < 0) return INJECTIVE;
        if ((r -= binary) < 0) return BINARY;
        if ((r -= symmetric) < 0) return SYMMETRIC;
        // occasionally fall through due to rounding error
    }
}

inline const Sampler::BoundedSampler & Sampler::bounded_sampler (
        size_t max_depth) const
{
    if (unlikely(max_depth >= m_bounded_samplers.size())) {
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
        Ob ob = try_insert_random_nullary();
        for (size_t depth = 1; depth; ++depth) {
            ob = try_insert_random_compound(ob, depth - 1);
        }
    } catch (InsertException e) {
        return e.inserted;
    }

    POMAGMA_ERROR("sampler failed");
    return 0;
}

inline Ob Sampler::try_insert_random_compound (Ob ob, size_t max_depth) const
{
    const BoundedSampler & sampler = bounded_sampler(max_depth);
    Arity arity = sampler.sample_compound_arity();
    switch (arity) {
        case NULLARY: {
            POMAGMA_ERROR("unreachable");
        } break;

        case INJECTIVE: {
            return try_insert_random_injective(ob);
        } break;

        case BINARY: {
            Ob other = try_insert_random(max_depth);
            if (random_bool(0.5)) std::swap(ob, other);
            return try_insert_random_binary(ob, other);
        } break;

        case SYMMETRIC: {
            Ob other = try_insert_random(max_depth);
            return try_insert_random_symmetric(ob, other);
        } break;
    }

    POMAGMA_ERROR("unreachable");
    return 0;
}

Ob Sampler::try_insert_random (size_t max_depth) const
{
    const BoundedSampler & sampler = bounded_sampler(max_depth);
    Arity arity = sampler.sample_arity();
    switch (arity) {
        case NULLARY: {
            return try_insert_random_nullary();
        } break;

        case INJECTIVE: {
            Ob key = try_insert_random(max_depth);
            return try_insert_random_injective(key);
        } break;

        case BINARY: {
            Ob lhs = try_insert_random(max_depth);
            Ob rhs = try_insert_random(max_depth);
            return try_insert_random_binary(lhs, rhs);
        } break;

        case SYMMETRIC: {
            Ob lhs = try_insert_random(max_depth);
            Ob rhs = try_insert_random(max_depth);
            return try_insert_random_symmetric(lhs, rhs);
        } break;
    }

    POMAGMA_ERROR("unreachable");
    return 0;
}

Ob Sampler::try_insert_random_nullary () const
{
    auto & fun = * sample(m_nullary_probs, m_nullary_prob);
    if (Ob val = fun.find()) {
        val = m_carrier.find(val);
        return val;
    } else {
        if (Ob val = m_carrier.try_insert()) {
            fun.insert(val);
            throw(InsertException(val));
        } else {
            throw(InsertException(0));
        }
    }
}

Ob Sampler::try_insert_random_injective (Ob key) const
{
    auto & fun = * sample(m_injective_probs, m_injective_prob);
    if (Ob val = fun.find(key)) {
        val = m_carrier.find(val);
        return val;
    } else {
        if (Ob val = m_carrier.try_insert()) {
            fun.insert(key, val);
            throw(InsertException(val));
        } else {
            throw(InsertException(0));
        }
    }
}

Ob Sampler::try_insert_random_binary (Ob lhs, Ob rhs) const
{
    auto & fun = * sample(m_binary_probs, m_binary_prob);
    if (Ob val = fun.find(lhs, rhs)) {
        val = m_carrier.find(val);
        return val;
    } else {
        if (Ob val = m_carrier.try_insert()) {
            fun.insert(lhs, rhs, val);
            throw(InsertException(val));
        } else {
            throw(InsertException(0));
        }
    }
}

Ob Sampler::try_insert_random_symmetric (Ob lhs, Ob rhs) const
{
    auto & fun = * sample(m_symmetric_probs, m_symmetric_prob);
    if (Ob val = fun.find(lhs, rhs)) {
        val = m_carrier.find(val);
        return val;
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
