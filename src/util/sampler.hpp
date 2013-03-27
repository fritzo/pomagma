#pragma once

// Assumes the following are defined:
// Ob
// Carrier
// NullaryFunction
// InjectiveFunction
// BinaryFunction
// SymmetricFunction
#include "util.hpp"
#include "signature.hpp"
#include "threading.hpp"

namespace pomagma
{

class Sampler : noncopyable
{
    Signature & m_signature;

    std::unordered_map<const NullaryFunction *, float> m_nullary_probs;
    std::unordered_map<const InjectiveFunction *, float> m_injective_probs;
    std::unordered_map<const BinaryFunction *, float> m_binary_probs;
    std::unordered_map<const SymmetricFunction *, float> m_symmetric_probs;

    float m_nullary_prob;
    float m_injective_prob;
    float m_binary_prob;
    float m_symmetric_prob;

    enum Arity { NULLARY, INJECTIVE, BINARY, SYMMETRIC };
    class BoundedSampler
    {
        float injective;
        float binary;
        float symmetric;
        float total;
        float compound_injective;
        float compound_binary;
        float compound_symmetric;
        float compound_total;

    public:

        BoundedSampler () { POMAGMA_ERROR("unused"); }
        BoundedSampler (const Sampler & sampler);
        BoundedSampler (const Sampler & sampler, const BoundedSampler & prev);

        Arity sample_arity (rng_t & rng) const;
        Arity sample_compound_arity (rng_t & rng) const;
    } __attribute__((aligned(64)));
    mutable std::vector<BoundedSampler> m_bounded_samplers;
    mutable SharedMutex m_bounded_samplers_mutex;
    const BoundedSampler & bounded_sampler (size_t max_depth) const;

    mutable std::atomic<uint_fast64_t> m_sample_count;
    mutable std::atomic<uint_fast64_t> m_reject_count;
    mutable std::atomic<uint_fast64_t> m_arity_sample_count;
    mutable std::atomic<uint_fast64_t> m_compound_arity_sample_count;

public:

    Sampler (Signature & signature);

    void validate () const;
    void log_stats () const;

    void set_prob (const std::string & name, float prob);

    class Policy; // implementation-specific
    Ob try_insert_random (rng_t & rng, Policy & policy) const;

private:

    const Carrier & carrier () const { return * m_signature.carrier(); }

    void set_prob (const NullaryFunction * fun, float prob);
    void set_prob (const InjectiveFunction * fun, float prob);
    void set_prob (const BinaryFunction * fun, float prob);
    void set_prob (const SymmetricFunction * fun, float prob);

    template<class Function>
    bool try_set_prob_ (
            const std::unordered_map<std::string, Function *> & funs,
            const std::string & name,
            float prob);

    struct ObInsertedException
    {
        Ob inserted;
        ObInsertedException (Ob i) : inserted(i) {}
    };
    struct ObRejectedException
    {
        ObRejectedException () {}
    };
    struct InsertionFailedException
    {
        InsertionFailedException () {}
    };

    Ob insert_random (
            size_t max_depth,
            rng_t & rng,
            Policy & policy) const;
    Ob insert_random_compound (
            Ob ob,
            size_t max_depth,
            rng_t & rng,
            Policy & policy) const;
    Ob insert_random_nullary (
            rng_t & rng,
            Policy & policy) const;
    Ob insert_random_injective (
            Ob key,
            rng_t & rng,
            Policy & policy) const;
    Ob insert_random_binary (
            Ob lhs,
            Ob rhs,
            rng_t & rng,
            Policy & policy) const;
    Ob insert_random_symmetric (
            Ob lhs,
            Ob rhs,
            rng_t & rng,
            Policy & policy) const;

    Ob check_insert (
            const NullaryFunction * fun,
            Policy & policy) const;
    Ob check_insert (
            const InjectiveFunction * fun,
            Ob key,
            Policy & policy) const;
    Ob check_insert (
            const BinaryFunction * fun,
            Ob lhs,
            Ob rhs,
            Policy & policy) const;
    Ob check_insert (
            const SymmetricFunction * fun,
            Ob lhs,
            Ob rhs,
            Policy & policy) const;
};

} // namespace pomagma
