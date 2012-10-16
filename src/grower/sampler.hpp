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

    std::unordered_map<const NullaryFunction *, float> m_nullary_probs;
    std::unordered_map<const InjectiveFunction *, float> m_injective_probs;
    std::unordered_map<const BinaryFunction *, float> m_binary_probs;
    std::unordered_map<const SymmetricFunction *, float> m_symmetric_probs;
    float m_nullary_prob;
    float m_injective_prob;
    float m_binary_prob;
    float m_symmetric_prob;

public:

    Sampler (Carrier & carrier);

    void set_prob (const NullaryFunction * fun, float prob);
    void set_prob (const InjectiveFunction * fun, float prob);
    void set_prob (const BinaryFunction * fun, float prob);
    void set_prob (const SymmetricFunction * fun, float prob);

    void unsafe_insert_random (); // TODO make safe as try_insert

private:

    std::pair<Ob, bool> try_insert_random ();
};

} // namespace pomagma
