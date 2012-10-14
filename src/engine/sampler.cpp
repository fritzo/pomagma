#include "sampler.hpp"
#include "aligned_alloc.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"

namespace pomagma {

Sampler::Sampler (Carrier & carrier)
    : m_carrier(carrier),
      m_probs(alloc_blocks<float>(1 + carrier.item_dim())),
      m_ephemeral(carrier.item_dim())
{
    zero_blocks(m_probs, 1 + carrier.item_dim());

    m_ephemeral.copy_from(carrier.support());
    for (const auto & pair : m_nullary_probs) {
        const auto & fun = * pair.first;
        Ob ob = fun.find();
        m_ephemeral.remove(ob);
    }
}

Sampler::~Sampler ()
{
    free_blocks(m_probs);
}

void Sampler::update_all ()
{
    for (auto iter = m_carrier.iter(); iter.ok(); iter.next()) {
        update_one(*iter);
    }
}

void Sampler::update_one (Ob ob)
{
    m_probs[ob] = compute_prob(ob);
}

float Sampler::compute_prob (Ob ob) const
{
    const float * restrict probs = m_probs;

    float prob = 0;

    for (const auto & pair : m_nullary_probs) {
        const auto & fun = * pair.first;
        if (fun.find() == ob) {
            const float coeff = pair.second;
            prob += coeff;
        }
    }

    for (const auto & pair : m_injective_probs) {
        const auto & fun = * pair.first;
        if (Ob inv = fun.inverse_find(ob)) {
            const float coeff = pair.second;
            prob += coeff * probs[inv];
        }
    }

    for (const auto & pair : m_binary_probs) {
        const auto & fun = * pair.first;
        double sum = 0;
        for (auto iter = fun.iter_val(ob); iter.ok(); iter.next()) {
            sum += probs[iter.lhs()] * probs[iter.rhs()];
        }
        const float coeff = pair.second;
        prob += coeff * sum;
    }

    for (const auto & pair : m_symmetric_probs) {
        const auto & fun = * pair.first;
        double sum = 0;
        for (auto iter = fun.iter_val(ob); iter.ok(); iter.next()) {
            sum += probs[iter.lhs()] * probs[iter.rhs()];
        }
        const float coeff = pair.second;
        prob += coeff * sum;
    }

    return prob;
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

void Sampler::unsafe_insert_random ()
{
    // TODO ASSERT(all obs are rep obs)
    // TODO measure rejection rate
    while (true) {
        auto pair = try_insert_random();
        bool inserted = pair.second;
        if (inserted) {
            return;
        }
    }
}

std::pair<Ob, bool> Sampler::try_insert_random ()
{
    while (true) {
        float r = random_01();

        if ((r -= m_nullary_prob) < 0) {
            auto & fun = * sample(m_nullary_probs, m_nullary_prob);
            Ob val = fun.find();
            return std::make_pair(val, false);
        }

        auto arg1_inserted = try_insert_random();
        if (arg1_inserted.second) return arg1_inserted;
        Ob arg1 = arg1_inserted.first;

        if ((r -= m_injective_prob) < 0) {
            auto & fun = * sample(m_injective_probs, m_injective_prob);
            if (Ob val = fun.find(arg1)) {
                return std::make_pair(val, false);
            } else {
                Ob val = m_carrier.unsafe_insert();
                fun.insert(arg1, val);
                return std::make_pair(val, true);
            }
        }

        auto arg2_inserted = try_insert_random();
        if (arg2_inserted.second) return arg2_inserted;
        Ob arg2 = arg2_inserted.first;

        if ((r -= m_binary_prob) < 0) {
            auto & fun = * sample(m_binary_probs, m_binary_prob);
            if (Ob val = fun.find(arg1, arg2)) {
                return std::make_pair(val, false);
            } else {
                Ob val = m_carrier.unsafe_insert();
                fun.insert(arg1, arg2, val);
                return std::make_pair(val, true);
            }
        }

        if ((r -= m_symmetric_prob) < 0) {
            auto & fun = * sample(m_symmetric_probs, m_symmetric_prob);
            if (Ob val = fun.find(arg1, arg2)) {
                return std::make_pair(val, false);
            } else {
                Ob val = m_carrier.unsafe_insert();
                fun.insert(arg1, arg2, val);
                return std::make_pair(val, true);
            }
        }

        // occasionally fall through due to rounding error
    }
}

Ob Sampler::unsafe_remove_random ()
{
    // TODO ASSERT(all obs are rep obs)
    TODO("chose ephemeral ob WRT recursive reciprocal prob"
         "\n(ie the prob mass that would be lost from db on remval)");
}

} // namespace pomagma
