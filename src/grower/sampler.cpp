#include "sampler.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"

namespace pomagma
{

Sampler::Sampler (Carrier & carrier)
    : m_carrier(carrier)
{
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

void Sampler::declare (const std::string & name, const NullaryFunction & fun)
{
    m_nullary_funs[name] = & fun;
}

void Sampler::declare (const std::string & name, const InjectiveFunction & fun)
{
    m_injective_funs[name] = & fun;
}

void Sampler::declare (const std::string & name, const BinaryFunction & fun)
{
    m_binary_funs[name] = & fun;
}

void Sampler::declare (const std::string & name, const SymmetricFunction & fun)
{
    m_symmetric_funs[name] = & fun;
}

void Sampler::set_prob (const NullaryFunction * fun, float prob)
{
    m_nullary_probs[fun] = prob;
    m_nullary_prob = sum(m_nullary_probs);
}

void Sampler::set_prob (const InjectiveFunction * fun, float prob)
{
    m_injective_probs[fun] = prob;
    m_injective_prob = sum(m_injective_probs);
}

void Sampler::set_prob (const BinaryFunction * fun, float prob)
{
    m_binary_probs[fun] = prob;
    m_binary_prob = sum(m_binary_probs);
}

void Sampler::set_prob (const SymmetricFunction * fun, float prob)
{
    m_symmetric_probs[fun] = prob;
    m_symmetric_prob = sum(m_symmetric_probs);
}

template<class Function>
bool Sampler::try_set_prob_ (
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
};

bool Sampler::try_insert_random ()
{
    while (m_carrier.item_count() < m_carrier.item_dim()) {
        auto pair = try_insert_random_();
        bool inserted = pair.second;
        if (inserted) {
            return true;
        }
    }
    return false;
}

std::pair<Ob, bool> Sampler::try_insert_random_ ()
{
    while (true) {
        float r = random_01();

        if ((r -= m_nullary_prob) < 0) {
            auto & fun = * sample(m_nullary_probs, m_nullary_prob);
            if (Ob val = fun.find()) {
                val = m_carrier.find(val);
                return std::make_pair(val, false);
            } else {
                return std::make_pair(0, false);
            }
        }

        auto arg1_inserted = try_insert_random_();
        if (arg1_inserted.second) return arg1_inserted;
        Ob arg1 = arg1_inserted.first;

        if ((r -= m_injective_prob) < 0) {
            auto & fun = * sample(m_injective_probs, m_injective_prob);
            if (Ob val = fun.find(arg1)) {
                val = m_carrier.find(val);
                return std::make_pair(val, false);
            } else {
                if (Ob val = m_carrier.try_insert()) {
                    fun.insert(arg1, val);
                    return std::make_pair(val, true);
                } else {
                    return std::make_pair(0, false);
                }
            }
        }

        auto arg2_inserted = try_insert_random_();
        if (arg2_inserted.second) return arg2_inserted;
        Ob arg2 = arg2_inserted.first;

        if ((r -= m_binary_prob) < 0) {
            auto & fun = * sample(m_binary_probs, m_binary_prob);
            if (Ob val = fun.find(arg1, arg2)) {
                val = m_carrier.find(val);
                return std::make_pair(val, false);
            } else {
                if (Ob val = m_carrier.try_insert()) {
                    fun.insert(arg1, arg2, val);
                    return std::make_pair(val, true);
                } else {
                    return std::make_pair(0, false);
                }
            }
        }

        if ((r -= m_symmetric_prob) < 0) {
            auto & fun = * sample(m_symmetric_probs, m_symmetric_prob);
            if (Ob val = fun.find(arg1, arg2)) {
                val = m_carrier.find(val);
                return std::make_pair(val, false);
            } else {
                if (Ob val = m_carrier.try_insert()) {
                    fun.insert(arg1, arg2, val);
                    return std::make_pair(val, true);
                } else {
                    return std::make_pair(0, false);
                }
            }
        }

        // occasionally fall through due to rounding error
    }
}

} // namespace pomagma
