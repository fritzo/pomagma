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

    std::unordered_map<std::string, const NullaryFunction *> m_nullary_funs;
    std::unordered_map<std::string, const InjectiveFunction *> m_injective_funs;
    std::unordered_map<std::string, const BinaryFunction *> m_binary_funs;
    std::unordered_map<std::string, const SymmetricFunction *> m_symmetric_funs;

    std::unordered_map<const NullaryFunction *, float> m_nullary_probs;
    std::unordered_map<const InjectiveFunction *, float> m_injective_probs;
    std::unordered_map<const BinaryFunction *, float> m_binary_probs;
    std::unordered_map<const SymmetricFunction *, float> m_symmetric_probs;

    float m_nullary_prob;
    float m_injective_prob;
    float m_binary_prob;
    float m_symmetric_prob;

    enum Arity { NULLARY, INJECTIVE, BINARY, SYMMETRIC };
    struct BoundedSampler
    {
        float nullary;
        float injective;
        float binary;
        float symmetric;
        float total;

        BoundedSampler () {}

        // base case
        BoundedSampler (const Sampler & sampler)
            : nullary(sampler.m_nullary_prob),
              injective(0),
              binary(0),
              symmetric(0),
              total(nullary)
        {
        }
        // induction step
        BoundedSampler (const Sampler & sampler, const BoundedSampler & prev)
            : nullary(sampler.m_nullary_prob),
              injective(sampler.m_injective_prob * prev.total),
              binary(sampler.m_binary_prob * (prev.total * prev.total)),
              symmetric(sampler.m_symmetric_prob * (prev.total * prev.total)),
              total(nullary + injective + binary + symmetric)
        {
        }

        Arity sample_arity () const;
        Arity sample_compound_arity () const;
    };
    mutable std::vector<BoundedSampler> m_bounded_samplers;
    const BoundedSampler & bounded_sampler (size_t max_depth) const;

public:

    Sampler (Carrier & carrier);

    void validate () const;

    void declare (const std::string & name, const NullaryFunction & fun);
    void declare (const std::string & name, const InjectiveFunction & fun);
    void declare (const std::string & name, const BinaryFunction & fun);
    void declare (const std::string & name, const SymmetricFunction & fun);

    void set_prob (const std::string &, float prob);

    Ob try_insert_random () const;

private:

    void set_prob (const NullaryFunction * fun, float prob);
    void set_prob (const InjectiveFunction * fun, float prob);
    void set_prob (const BinaryFunction * fun, float prob);
    void set_prob (const SymmetricFunction * fun, float prob);

    template<class Function>
    bool try_set_prob_ (
            const std::unordered_map<std::string, const Function *> & funs,
            const std::string & name,
            float prob);

    struct InsertException
    {
        Ob inserted;
        InsertException (Ob i) : inserted(i) {}
    };
    Ob try_insert_random_compound (Ob ob, size_t max_depth) const;
    Ob try_insert_random (size_t max_depth) const;
    Ob try_insert_random_nullary () const;
    Ob try_insert_random_injective (Ob key) const;
    Ob try_insert_random_binary (Ob lhs, Ob rhs) const;
    Ob try_insert_random_symmetric (Ob lhs, Ob rhs) const;
};

} // namespace pomagma
