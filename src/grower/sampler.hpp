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

public:

    Sampler (Carrier & carrier);

    void validate () const;

    void declare (const std::string & name, const NullaryFunction & fun);
    void declare (const std::string & name, const InjectiveFunction & fun);
    void declare (const std::string & name, const BinaryFunction & fun);
    void declare (const std::string & name, const SymmetricFunction & fun);

    void set_prob (const std::string &, float prob);

    bool try_insert_random () const;

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

    std::pair<Ob, bool> try_insert_random_ () const;
};

} // namespace pomagma
