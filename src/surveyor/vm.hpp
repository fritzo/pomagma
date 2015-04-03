#pragma once

#include "theory.hpp"

namespace pomagma
{
namespace vm
{

enum OpCode
{
    IF_EQUAL,
    IF_UNARY_RELATION,
    IF_BINARY_RELATION,
    FOR_ALL,
    FOR_UNARY_RELATION,
    FOR_BINARY_RELATION_LHS,
    FOR_BINARY_RELATION_RHS,
    FOR_NULLARY_FUNCTION,
    FOR_INJECTIVE_FUNCTION,
    FOR_INJECTIVE_FUNCTION_KEY,
    FOR_INJECTIVE_FUNCTION_VAL,
    FOR_BINARY_FUNCTION_LHS,
    FOR_BINARY_FUNCTION_RHS,
    FOR_BINARY_FUNCTION_VAL,
    FOR_BINARY_FUNCTION_LHS_VAL,
    FOR_BINARY_FUNCTION_RHS_VAL,
    FOR_BINARY_FUNCTION_LHS_RHS,
    FOR_SYMMETRIC_FUNCTION_LHS,
    FOR_SYMMETRIC_FUNCTION_VAL,
    FOR_SYMMETRIC_FUNCTION_LHS_VAL,
    FOR_SYMMETRIC_FUNCTION_LHS_RHS,
    ENSURE_EQUAL,
    ENSURE_UNARY_RELATION,
    ENSURE_BINARY_RELATION,
    ENSURE_INJECTIVE_FUNCTION,
    ENSURE_BINARY_FUNCTION,
    ENSURE_SYMMETRIC_FUNCTION,
    ENSURE_COMPOUND
};

struct Operation
{
    uint8_t data[8] __attribute__ ((aligned (8)));

    OpCode op_code () const { return static_cast<OpCode>(data[0]); }
    const uint8_t * args () const { return data + 1; }
};

class VirtualMachine
{
public:

    VirtualMachine (Signature & signature);
    void execute (const Operation * program);

private:

    Ob m_obs[256];
    UnaryRelation * m_unary_relations[256];
    BinaryRelation * m_binary_relations[256];
    NullaryFunction * m_nullary_functions[256];
    InjectiveFunction * m_injective_functions[256];
    BinaryFunction * m_binary_functions[256];
    SymmetricFunction * m_symmetric_functions[256];
    Carrier * m_carrier;

    uint8_t pop_arg (const uint8_t * & args)
    {
        POMAGMA_ASSERT5(
            reinterpret_cast<const size_t &>(args) & 7,
            "tried to pop_arg(-) past end of args");

        return *args++;
    }

    Ob & pop_ob (const uint8_t * & args) { return m_obs[pop_arg(args)]; }

    UnaryRelation & pop_unary_relation (const uint8_t * & args)
    {
        return * m_unary_relations[pop_arg(args)];
    }

    BinaryRelation & pop_binary_relation (const uint8_t * & args)
    {
        return * m_binary_relations[pop_arg(args)];
    }

    NullaryFunction & pop_nullary_function (const uint8_t * & args)
    {
        return * m_nullary_functions[pop_arg(args)];
    }

    InjectiveFunction & pop_injective_function (const uint8_t * & args)
    {
        return * m_injective_functions[pop_arg(args)];
    }

    BinaryFunction & pop_binary_function (const uint8_t * & args)
    {
        return * m_binary_functions[pop_arg(args)];
    }

    SymmetricFunction & pop_symmetric_function (const uint8_t * & args)
    {
        return * m_symmetric_functions[pop_arg(args)];
    }

    Carrier & carrier () { return * m_carrier; }
};

} // namespace vm
} // namespacepomagma
