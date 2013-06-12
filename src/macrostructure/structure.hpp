#pragma once

#include <pomagma/platform/util.hpp>
#include <pomagma/platform/signature.hpp>

namespace pomagma
{

class Structure : noncopyable
{
    Signature m_signature;

public:

    Structure () {}

    Signature & signature () { return m_signature; }
    Carrier & carrier () { return * m_signature.carrier(); }
    BinaryRelation & binary_relation(const std::string & name);
    NullaryFunction & nullary_function(const std::string & name);
    InjectiveFunction & injective_function(const std::string & name);
    BinaryFunction & binary_function(const std::string & name);
    SymmetricFunction & symmetric_function(const std::string & name);

    void validate_consistent ();
    void validate ();
    void clear ();
    void load (const std::string & filename, size_t extra_item_dim = 0);
    void dump (const std::string & filename);
    void init_signature (Structure & other, size_t item_dim);
};

inline BinaryRelation & Structure::binary_relation(
        const std::string & name)
{
    auto * result = m_signature.binary_relations(name);
    POMAGMA_ASSERT(result, "missing binary relation " << name);
    return * result;
}

inline NullaryFunction & Structure::nullary_function(
        const std::string & name)
{
    auto * result = m_signature.nullary_functions(name);
    POMAGMA_ASSERT(result, "missing nullary function " << name);
    return * result;
}

inline InjectiveFunction & Structure::injective_function(
        const std::string & name)
{
    auto * result = m_signature.injective_functions(name);
    POMAGMA_ASSERT(result, "missing injective function " << name);
    return * result;
}

inline BinaryFunction & Structure::binary_function(
        const std::string & name)
{
    auto * result = m_signature.binary_functions(name);
    POMAGMA_ASSERT(result, "missing binary function " << name);
    return * result;
}

inline SymmetricFunction & Structure::symmetric_function(
        const std::string & name)
{
    auto * result = m_signature.symmetric_functions(name);
    POMAGMA_ASSERT(result, "missing symmetric function " << name);
    return * result;
}

} // namespace pomagma
