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

    // TODO maintain removal probs
    //std::atomic<float> * const m_probs;
    float * const m_probs;
    DenseSet m_ephemeral;

public:

    Sampler (Carrier & carrier);
    ~Sampler ();

    // TODO init, set probs

    // TODO update insert+remove weights n+n background threads
    void update_all ();
    void update_one (Ob ob);

    void unsafe_insert_random ();
    void unsafe_remove_random ();

    void insert () { TODO("deal with m_ephemeral"); }
    void remove (Ob ob) { m_probs[ob] = 0; TODO("deal with m_ephemeral"); }
    void merge (Ob dep) { m_probs[dep] = 0; TODO("deal with m_ephemeral"); }

private:

    float compute_prob (Ob ob) const;

    std::pair<Ob, bool> try_insert_random ();
};

} // namespace pomagma
