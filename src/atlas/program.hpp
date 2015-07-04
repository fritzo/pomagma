#pragma once

#include "program_fwd.hpp"
#include "message.hpp"
#include <fstream>
#include <map>
#include <sstream>
#include <typeinfo>
#include <unordered_set>

namespace pomagma {
namespace vm {

//----------------------------------------------------------------------------
// 8-bit floating points

// 4 bit significand, 4 bit exponent
constexpr inline size_t eval_float44 (size_t num)
{
    return ((num % 16u) + 16u) * (1u << (num / 16u)) - 16u;
}

static_assert(eval_float44(0) == 0, "programmer error");
static_assert(eval_float44(1) == 1, "programmer error");
static_assert(eval_float44(2) == 2, "programmer error");
static_assert(eval_float44(3) == 3, "programmer error");
static_assert(eval_float44(10) == 10, "programmer error");
static_assert(eval_float44(45) == 100, "programmer error");
static_assert(eval_float44(96) == 1008, "programmer error");
static_assert(eval_float44(148) == 10224, "programmer error");
static_assert(eval_float44(201) == 102384, "programmer error");
static_assert(eval_float44(255) == 1015792, "programmer error");

// 5 bit significand, 3 bit exponent
constexpr inline size_t eval_float53 (size_t num)
{
    return ((num % 32u) + 32u) * (1u << (num / 32u)) - 32u;
}

static_assert(eval_float53(0) == 0, "programmer error");
static_assert(eval_float53(1) == 1, "programmer error");
static_assert(eval_float53(2) == 2, "programmer error");
static_assert(eval_float53(3) == 3, "programmer error");
static_assert(eval_float53(10) == 10, "programmer error");
static_assert(eval_float53(65) == 100, "programmer error");
static_assert(eval_float53(161) == 1024, "programmer error");
static_assert(eval_float53(255) == 8032, "programmer error");

//----------------------------------------------------------------------------
// OpCode

enum OpArgType : uint8_t
{
    UINT8,
    NEW_OB,
    OB,
    NEW_SET,
    SET,
    UNARY_RELATION,
    BINARY_RELATION,
    NULLARY_FUNCTION,
    INJECTIVE_FUNCTION,
    BINARY_FUNCTION,
    SYMMETRIC_FUNCTION,
};

#define POMAGMA_OP_CODES(DO) \
    DO(PADDING, ({})) \
    DO(SEQUENCE, ({UINT8})) \
    DO(GIVEN_EXISTS, ({NEW_OB})) \
    DO(GIVEN_UNARY_RELATION, ({UNARY_RELATION, NEW_OB})) \
    DO(GIVEN_BINARY_RELATION, ({BINARY_RELATION, NEW_OB, NEW_OB})) \
    DO(GIVEN_NULLARY_FUNCTION, ({NULLARY_FUNCTION, NEW_OB})) \
    DO(GIVEN_INJECTIVE_FUNCTION, ({INJECTIVE_FUNCTION, NEW_OB, NEW_OB})) \
    DO(GIVEN_BINARY_FUNCTION, ({BINARY_FUNCTION, NEW_OB, NEW_OB, NEW_OB})) \
    DO(GIVEN_SYMMETRIC_FUNCTION, \
        ({SYMMETRIC_FUNCTION, NEW_OB, NEW_OB, NEW_OB})) \
    DO(LETS_UNARY_RELATION, ({UNARY_RELATION, NEW_SET})) \
    DO(LETS_BINARY_RELATION_LHS, ({BINARY_RELATION, OB, NEW_SET})) \
    DO(LETS_BINARY_RELATION_RHS, ({BINARY_RELATION, NEW_SET, OB})) \
    DO(LETS_INJECTIVE_FUNCTION, ({INJECTIVE_FUNCTION, NEW_SET})) \
    DO(LETS_INJECTIVE_FUNCTION_INVERSE, ({INJECTIVE_FUNCTION, NEW_SET})) \
    DO(LETS_BINARY_FUNCTION_LHS, ({BINARY_FUNCTION, OB, NEW_SET})) \
    DO(LETS_BINARY_FUNCTION_RHS, ({BINARY_FUNCTION, NEW_SET, OB})) \
    DO(LETS_SYMMETRIC_FUNCTION_LHS, ({SYMMETRIC_FUNCTION, OB, NEW_SET})) \
    DO(FOR_NEG, ({NEW_OB, SET})) \
    DO(FOR_NEG_NEG, ({NEW_OB, SET, SET})) \
    DO(FOR_POS_NEG, ({NEW_OB, SET, SET})) \
    DO(FOR_POS_NEG_NEG, ({NEW_OB, SET, SET, SET})) \
    DO(FOR_POS_POS, ({NEW_OB, SET, SET})) \
    DO(FOR_POS_POS_NEG, ({NEW_OB, SET, SET, SET})) \
    DO(FOR_POS_POS_NEG_NEG, ({NEW_OB, SET, SET, SET, SET})) \
    DO(FOR_POS_POS_POS, ({NEW_OB, SET, SET, SET})) \
    DO(FOR_POS_POS_POS_POS, ({NEW_OB, SET, SET, SET, SET})) \
    DO(FOR_POS_POS_POS_POS_POS, ({NEW_OB, SET, SET, SET, SET, SET})) \
    DO(FOR_POS_POS_POS_POS_POS_POS, ({NEW_OB, SET, SET, SET, SET, SET, SET})) \
    DO(FOR_ALL, ({NEW_OB})) \
    DO(FOR_UNARY_RELATION, ({UNARY_RELATION, NEW_OB})) \
    DO(FOR_BINARY_RELATION_LHS, ({BINARY_RELATION, OB, NEW_OB})) \
    DO(FOR_BINARY_RELATION_RHS, ({BINARY_RELATION, NEW_OB, OB})) \
    DO(FOR_NULLARY_FUNCTION, ({NULLARY_FUNCTION, NEW_OB})) \
    DO(FOR_INJECTIVE_FUNCTION, ({INJECTIVE_FUNCTION, NEW_OB, NEW_OB})) \
    DO(FOR_INJECTIVE_FUNCTION_KEY, ({INJECTIVE_FUNCTION, OB, NEW_OB})) \
    DO(FOR_INJECTIVE_FUNCTION_VAL, ({INJECTIVE_FUNCTION, NEW_OB, OB})) \
    DO(FOR_BINARY_FUNCTION_LHS, ({BINARY_FUNCTION, OB, NEW_OB, NEW_OB})) \
    DO(FOR_BINARY_FUNCTION_RHS, ({BINARY_FUNCTION, NEW_OB, OB, NEW_OB})) \
    DO(FOR_BINARY_FUNCTION_VAL, ({BINARY_FUNCTION, NEW_OB, NEW_OB, OB})) \
    DO(FOR_BINARY_FUNCTION_LHS_VAL, ({BINARY_FUNCTION, OB, NEW_OB, OB})) \
    DO(FOR_BINARY_FUNCTION_RHS_VAL, ({BINARY_FUNCTION, NEW_OB, OB, OB})) \
    DO(FOR_BINARY_FUNCTION_LHS_RHS, ({BINARY_FUNCTION, OB, OB, NEW_OB})) \
    DO(FOR_SYMMETRIC_FUNCTION_LHS, ({SYMMETRIC_FUNCTION, OB, NEW_OB, NEW_OB})) \
    DO(FOR_SYMMETRIC_FUNCTION_VAL, ({SYMMETRIC_FUNCTION, NEW_OB, NEW_OB, OB})) \
    DO(FOR_SYMMETRIC_FUNCTION_LHS_VAL, ({SYMMETRIC_FUNCTION, OB, NEW_OB, OB})) \
    DO(FOR_SYMMETRIC_FUNCTION_LHS_RHS, ({SYMMETRIC_FUNCTION, OB, OB, NEW_OB})) \
    DO(FOR_BLOCK, ({})) \
    DO(IF_BLOCK, ({OB})) \
    DO(IF_EQUAL, ({OB, OB})) \
    DO(IF_UNARY_RELATION, ({UNARY_RELATION, OB})) \
    DO(IF_BINARY_RELATION, ({BINARY_RELATION, OB, OB})) \
    DO(IF_NULLARY_FUNCTION, ({NULLARY_FUNCTION, OB})) \
    DO(IF_INJECTIVE_FUNCTION, ({INJECTIVE_FUNCTION, OB, OB})) \
    DO(IF_BINARY_FUNCTION, ({BINARY_FUNCTION, OB, OB, OB})) \
    DO(IF_SYMMETRIC_FUNCTION, ({SYMMETRIC_FUNCTION, OB, OB, OB})) \
    DO(LET_NULLARY_FUNCTION, ({NULLARY_FUNCTION, NEW_OB})) \
    DO(LET_INJECTIVE_FUNCTION, ({INJECTIVE_FUNCTION, OB, NEW_OB})) \
    DO(LET_BINARY_FUNCTION, ({BINARY_FUNCTION, OB, OB, NEW_OB})) \
    DO(LET_SYMMETRIC_FUNCTION, ({SYMMETRIC_FUNCTION, OB, OB, NEW_OB})) \
    DO(INFER_EQUAL, ({OB, OB})) \
    DO(INFER_UNARY_RELATION, ({UNARY_RELATION, OB})) \
    DO(INFER_BINARY_RELATION, ({BINARY_RELATION, OB, OB})) \
    DO(INFER_NULLARY_FUNCTION, ({NULLARY_FUNCTION, OB})) \
    DO(INFER_INJECTIVE_FUNCTION, ({INJECTIVE_FUNCTION, OB, OB})) \
    DO(INFER_BINARY_FUNCTION, ({BINARY_FUNCTION, OB, OB, OB})) \
    DO(INFER_SYMMETRIC_FUNCTION, ({SYMMETRIC_FUNCTION, OB, OB, OB})) \
    DO(INFER_NULLARY_NULLARY, ({NULLARY_FUNCTION, NULLARY_FUNCTION})) \
    DO(INFER_NULLARY_INJECTIVE, \
        ({NULLARY_FUNCTION, INJECTIVE_FUNCTION, OB})) \
    DO(INFER_NULLARY_BINARY, \
        ({NULLARY_FUNCTION, BINARY_FUNCTION, OB, OB})) \
    DO(INFER_NULLARY_SYMMETRIC, \
        ({NULLARY_FUNCTION, SYMMETRIC_FUNCTION, OB, OB})) \
    DO(INFER_INJECTIVE_INJECTIVE, \
        ({INJECTIVE_FUNCTION, OB, INJECTIVE_FUNCTION, OB})) \
    DO(INFER_INJECTIVE_BINARY, \
        ({INJECTIVE_FUNCTION, OB, BINARY_FUNCTION, OB, OB})) \
    DO(INFER_INJECTIVE_SYMMETRIC, \
        ({INJECTIVE_FUNCTION, OB, SYMMETRIC_FUNCTION, OB, OB})) \
    DO(INFER_BINARY_BINARY, \
        ({BINARY_FUNCTION, OB, OB, BINARY_FUNCTION, OB, OB})) \
    DO(INFER_BINARY_SYMMETRIC, \
        ({BINARY_FUNCTION, OB, OB, SYMMETRIC_FUNCTION, OB, OB})) \
    DO(INFER_SYMMETRIC_SYMMETRIC, \
        ({SYMMETRIC_FUNCTION, OB, OB, SYMMETRIC_FUNCTION, OB, OB}))

enum OpCode : uint8_t
{
#define DO(X, Y) X,
    POMAGMA_OP_CODES(DO)
#undef DO
};

extern const std::string g_op_code_names[];
extern const std::map<std::string, OpCode> g_op_codes;
extern const std::vector<std::vector<OpArgType>> g_op_code_arities;
static const size_t g_op_code_count = 0
#define DO(X, Y) +1
    POMAGMA_OP_CODES(DO)
#undef DO
;

//----------------------------------------------------------------------------
// Continuations.
//
// The serialized format is a sequence of protobuf-encoded Varint32 values:
//   [program_offset, context->obs[obs_used[0]], ..., context->obs[obs_used[n]]]
// where find_obs_used_by determines which obs are used by the program fragment
// at program_offset.

template<class Ob, class SetPtr>
inline void ProgramParser::dump_continuation (
        Program program,
        const Context_<Ob, SetPtr> * context,
        std::string & message)
{
    ptrdiff_t program_offset = program - m_program_data.data();
    if (POMAGMA_DEBUG_LEVEL) {
        POMAGMA_ASSERT_LE(0, program_offset);
        POMAGMA_ASSERT_LT(program_offset, m_program_data.size());
    }
    const std::vector<uint8_t> & obs_used = find_obs_used_by(program_offset);

    io::Varint32Writer writer(message, 1 + obs_used.size());
    writer.write(program_offset);
    for (auto index : obs_used) {
        writer.write(context->obs[index]);
    }
}

template<class Ob, class SetPtr>
inline Program ProgramParser::load_continuation (
        Context_<Ob, SetPtr> * context,
        const std::string & message)
{
    if (POMAGMA_DEBUG_LEVEL) { context->clear(); }

    io::Varint32Reader reader(message);
    size_t program_offset = reader.read();
    if (POMAGMA_DEBUG_LEVEL) {
        POMAGMA_ASSERT_LT(program_offset, m_program_data.size());
    }
    for (uint8_t index : find_obs_used_by(program_offset)) {
        context->obs[index] = reader.read();
    }

    return m_program_data.data() + program_offset;
}

} // namespace vm
} // namespace pomagma
