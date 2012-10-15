#pragma once

#include "util.hpp"
#include "carrier.hpp"
#include <unordered_map>

namespace pomagma {

class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;

class Sampler
{
    Carrier & m_carrier;

    std::unordered_map<NullaryFunction *, float> m_nullary_probs;
    std::unordered_map<InjectiveFunction *, float> m_injective_probs;
    std::unordered_map<BinaryFunction *, float> m_binary_probs;
    std::unordered_map<SymmetricFunction *, float> m_symmetric_probs;
    float m_nullary_prob;
    float m_injective_prob;
    float m_binary_prob;
    float m_symmetric_prob;

public:

    Sampler (Carrier & carrier);

    // TODO init, set probs

    void unsafe_insert_random ();

private:

    std::pair<Ob, bool> try_insert_random ();
};

} // namespace pomagma
