#pragma once

#include <pomagma/platform/aligned_alloc.hpp>
#include "theory.hpp"

namespace pomagma
{
namespace vm
{

#define OP_CODES(DO) \
    DO(IF_EQUAL) \
    DO(IF_UNARY_RELATION) \
    DO(IF_BINARY_RELATION) \
    DO(SET_UNARY_RELATION) \
    DO(SET_BINARY_RELATION_LHS) \
    DO(SET_BINARY_RELATION_RHS) \
    DO(SET_INJECTIVE_FUNCTION) \
    DO(SET_INJECTIVE_FUNCTION_INVERSE) \
    DO(SET_BINARY_FUNCTION_LHS) \
    DO(SET_BINARY_FUNCTION_RHS) \
    DO(SET_SYMMETRIC_FUNCTION_LHS) \
    DO(FOR_INTERSECTION_2) \
    DO(FOR_INTERSECTION_3) \
    DO(FOR_INTERSECTION_4) \
    DO(FOR_INTERSECTION_5) \
    DO(FOR_INTERSECTION_6) \
    DO(FOR_ALL) \
    DO(FOR_UNARY_RELATION) \
    DO(FOR_BINARY_RELATION_LHS) \
    DO(FOR_BINARY_RELATION_RHS) \
    DO(FOR_NULLARY_FUNCTION) \
    DO(FOR_INJECTIVE_FUNCTION) \
    DO(FOR_INJECTIVE_FUNCTION_KEY) \
    DO(FOR_INJECTIVE_FUNCTION_VAL) \
    DO(FOR_BINARY_FUNCTION_LHS) \
    DO(FOR_BINARY_FUNCTION_RHS) \
    DO(FOR_BINARY_FUNCTION_VAL) \
    DO(FOR_BINARY_FUNCTION_LHS_VAL) \
    DO(FOR_BINARY_FUNCTION_RHS_VAL) \
    DO(FOR_BINARY_FUNCTION_LHS_RHS) \
    DO(FOR_SYMMETRIC_FUNCTION_LHS) \
    DO(FOR_SYMMETRIC_FUNCTION_VAL) \
    DO(FOR_SYMMETRIC_FUNCTION_LHS_VAL) \
    DO(FOR_SYMMETRIC_FUNCTION_LHS_RHS) \
    DO(ENSURE_EQUAL) \
    DO(ENSURE_UNARY_RELATION) \
    DO(ENSURE_BINARY_RELATION) \
    DO(ENSURE_INJECTIVE_FUNCTION) \
    DO(ENSURE_BINARY_FUNCTION) \
    DO(ENSURE_SYMMETRIC_FUNCTION) \
    DO(ENSURE_COMPOUND)

enum OpCode
{
#define DO(X) X,
OP_CODES(DO)
#undef DO
};

const char * const OpCodeNames[] =
{
#define DO(X) #X,
OP_CODES(DO)
#undef DO
};

#undef OP_CODES

struct Operation
{
    uint8_t data[8];

    OpCode op_code () const { return static_cast<OpCode>(data[0]); }
    const uint8_t * args () const { return data + 1; }

    void validate_alignment () const
    {
        POMAGMA_ASSERT5(is_aligned(this, 8), "program is misaligned");
    }
} __attribute__ ((aligned (8)));

class VirtualMachine
{
public:

    VirtualMachine (Signature & signature);
    void execute (const Operation * program);

private:

    Ob m_obs[256];
    const std::atomic<Word> * m_sets[256];
    UnaryRelation * m_unary_relations[256];
    BinaryRelation * m_binary_relations[256];
    NullaryFunction * m_nullary_functions[256];
    InjectiveFunction * m_injective_functions[256];
    BinaryFunction * m_binary_functions[256];
    SymmetricFunction * m_symmetric_functions[256];
    Carrier & m_carrier;

    uint8_t pop_arg (const uint8_t * & args)
    {
        POMAGMA_ASSERT5(not is_aligned(args, 8), "pop_arg'd past end of args");
        return *args++;
    }

    Ob & pop_ob (const uint8_t * & args)
    {
        return m_obs[pop_arg(args)];
    }

    const std::atomic<Word> * & pop_set (const uint8_t * & args)
    {
        return m_sets[pop_arg(args)];
    }

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

    Carrier & carrier () { return m_carrier; }
    const DenseSet & support () { return m_carrier.support(); }
    size_t item_dim () { return support().item_dim(); }
    size_t word_dim () { return support().word_dim(); }

} __attribute__ ((aligned (64)));

} // namespace vm
} // namespacepomagma
