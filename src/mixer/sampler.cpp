#include "sampler.hpp"
#include "aligned_alloc.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"

namespace pomagma {

Sampler::Sampler (const Carrier & carrier)
    : m_carrier(carrier),
      m_weights(alloc_blocks<float>(1 + carrier.item_dim()))
{
    zero_blocks(m_weights, 1 + carrier.item_dim());
}

Sampler::~Sampler ()
{
    free_blocks(m_weights);
}

void Sampler::update_all ()
{
    for (auto iter = m_carrier.iter(); iter.ok(); iter.next()) {
        update_one(*iter);
    }
}

void Sampler::update_one (Ob ob)
{
    float * restrict weights = m_weights;

    double weight = 0;

    for (auto & pair : m_nullary_weights) {
        const auto & fun = * pair.first;
        if (fun.find() == ob) {
            weight += pair.second;
        }
    }

    for (auto & pair : m_injective_weights) {
        const auto & fun = * pair.first;
        const float coeff = pair.second;
        if (Ob inv = fun.inverse_find(ob)) {
            weight += coeff * weights[inv];
        }
    }

    for (auto & pair : m_binary_weights) {
        const auto & fun = * pair.first;
        const float coeff = pair.second;
        double sum = 0;
        for (auto iter = fun.iter_val(ob); iter.ok(); iter.next()) {
            sum += weights[iter.lhs()] * weights[iter.rhs()];
        }
        weight += coeff * sum;
    }

    for (auto & pair : m_symmetric_weights) {
        const auto & fun = * pair.first;
        const float coeff = pair.second;
        double sum = 0;
        for (auto iter = fun.iter_val(ob); iter.ok(); iter.next()) {
            sum += weights[iter.lhs()] * weights[iter.rhs()];
        }
        weight += coeff * sum;
    }

    weights[ob] = weight;
}

} // namespace pomagma
