#pragma once

#include "util.hpp"
#include "carrier.hpp"
#include <map>



namespace pomagma {

class NullaryFunction;
class InjectiveFunction;
class BinaryFunction;
class SymmetricFunction;

class Sampler
{
    const Carrier & m_carrier;

    std::map<const NullaryFunction *, float> m_nullary_weights;
    std::map<const InjectiveFunction *, float> m_injective_weights;
    std::map<const BinaryFunction *, float> m_binary_weights;
    std::map<const SymmetricFunction *, float> m_symmetric_weights;

    float * const m_weights;

public:

    Sampler (const Carrier & carrier);
    ~Sampler ();

    // TODO set weights

    void update_all ();
    void update_one (Ob ob);
};

} // namespace pomagma
