#include <map>
#include <unordered_set>
#include <typeinfo>
#include <sstream>
#include <fstream>
#include <algorithm>
#include "program.hpp"
#include "vm.hpp"

#define POMAGMA_TRACE_VM (false)

namespace pomagma {
namespace vm {

//----------------------------------------------------------------------------
// VirtualMachine

static_assert(VirtualMachine::for_block_op_code == FOR_BLOCK,
    "for_block_op_code does not match FOR_BLOCK");

template<class Table>
static void declare (
        const std::unordered_map<std::string, Table *> & unordered_map,
        Table * array[])
{
    POMAGMA_ASSERT(
        unordered_map.size() <= 256,
        "too many " << demangle(typeid(Table).name()) << " symbols: "
        "expected <= 256, actual = " << unordered_map.size());

    for (size_t i = 0; i < 256; ++i) {
        array[i] = nullptr;
    }

    std::map<std::string, Table *> sorted;
    sorted.insert(unordered_map.begin(), unordered_map.end());
    for (auto pair : sorted) {
        *array++ = pair.second;
    }
}

void VirtualMachine::load (Signature & signature)
{
    m_carrier = signature.carrier();

    declare(signature.unary_relations(), m_unary_relations);
    declare(signature.binary_relations(), m_binary_relations);
    declare(signature.nullary_functions(), m_nullary_functions);
    declare(signature.injective_functions(), m_injective_functions);
    declare(signature.binary_functions(), m_binary_functions);
    declare(signature.symmetric_functions(), m_symmetric_functions);
}

inline const UnaryRelation * VirtualMachine::unary_relation (
        uint8_t index) const
{
    auto ptr = m_unary_relations[index];
    POMAGMA_ASSERT(ptr, "missing unary_relation " << index);
    return ptr;
}

inline const BinaryRelation * VirtualMachine::binary_relation (
        uint8_t index) const
{
    auto ptr = m_binary_relations[index];
    POMAGMA_ASSERT(ptr, "missing binary_relation " << index);
    return ptr;
}

inline const NullaryFunction * VirtualMachine::nullary_function (
        uint8_t index) const
{
    auto ptr = m_nullary_functions[index];
    POMAGMA_ASSERT(ptr, "missing nullary_function " << index);
    return ptr;
}

inline const InjectiveFunction * VirtualMachine::injective_function (
        uint8_t index) const
{
    auto ptr = m_injective_functions[index];
    POMAGMA_ASSERT(ptr, "missing injective_function " << index);
    return ptr;
}

inline const BinaryFunction * VirtualMachine::binary_function (
        uint8_t index) const
{
    auto ptr = m_binary_functions[index];
    POMAGMA_ASSERT(ptr, "missing binary_function " << index);
    return ptr;
}

inline const SymmetricFunction * VirtualMachine::symmetric_function (
        uint8_t index) const
{
    auto ptr = m_symmetric_functions[index];
    POMAGMA_ASSERT(ptr, "missing symmetric_function " << index);
    return ptr;
}

static const char * const spaces_256 =
"                                                                "
"                                                                "
"                                                                "
"                                                                "
;

void VirtualMachine::_execute (Program program, Context * context) const
{
    OpCode op_code = pop_op_code(program);

    if (POMAGMA_TRACE_VM) {
        POMAGMA_ASSERT_LE(context->trace, 256);
        POMAGMA_DEBUG(
            (spaces_256 + 256 - context->trace) <<
            g_op_code_names[op_code]);
        ++context->trace;
    }

    switch (op_code) {

        case PADDING: {
            POMAGMA_ERROR("executed padding");
        } break;

        case SEQUENCE: {
            size_t jump = eval_float53(pop_arg(program));
            _execute(program, context);
            _execute(program + jump, context);
        } break;

        case GIVEN_EXISTS: {
            pop_ob(program, context);
            _execute(program, context);
        } break;

        case GIVEN_UNARY_RELATION: {
            pop_unary_relation(program);
            pop_ob(program, context);
            _execute(program, context);
        } break;

        case GIVEN_BINARY_RELATION: {
            pop_binary_relation(program);
            pop_ob(program, context);
            pop_ob(program, context);
            _execute(program, context);
        } break;

        case GIVEN_NULLARY_FUNCTION: {
            pop_nullary_function(program);
            _execute(program, context);
        } break;

        case GIVEN_INJECTIVE_FUNCTION: {
            pop_injective_function(program);
            pop_ob(program, context);
            _execute(program, context);
        } break;

        case GIVEN_BINARY_FUNCTION: {
            pop_binary_function(program);
            pop_ob(program, context);
            pop_ob(program, context);
            _execute(program, context);
        } break;

        case GIVEN_SYMMETRIC_FUNCTION: {
            pop_symmetric_function(program);
            pop_ob(program, context);
            pop_ob(program, context);
            _execute(program, context);
        } break;

        case LETS_UNARY_RELATION: {
            UnaryRelation & rel = pop_unary_relation(program);
            pop_set(program, context) = rel.get_set().raw_data();
            _execute(program, context);
        } break;

        case LETS_BINARY_RELATION_LHS: {
            BinaryRelation & rel = pop_binary_relation(program);
            Ob lhs = pop_ob(program, context);
            auto & rhs_set = pop_set(program, context);
            rhs_set = rel.get_Lx_set(lhs).raw_data();
            _execute(program, context);
        } break;

        case LETS_BINARY_RELATION_RHS: {
            BinaryRelation & rel = pop_binary_relation(program);
            auto & lhs_set = pop_set(program, context);
            Ob rhs = pop_ob(program, context);
            lhs_set = rel.get_Rx_set(rhs).raw_data();
            _execute(program, context);
        } break;

        case LETS_INJECTIVE_FUNCTION: {
            InjectiveFunction & fun = pop_injective_function(program);
            pop_set(program, context) = fun.defined().raw_data();
            _execute(program, context);
        } break;

        case LETS_INJECTIVE_FUNCTION_INVERSE: {
            InjectiveFunction & fun = pop_injective_function(program);
            pop_set(program, context) = fun.inverse_defined().raw_data();
            _execute(program, context);
        } break;

        case LETS_BINARY_FUNCTION_LHS: {
            BinaryFunction & fun = pop_binary_function(program);
            Ob lhs = pop_ob(program, context);
            auto & rhs_set = pop_set(program, context);
            rhs_set = fun.get_Lx_set(lhs).raw_data();
            _execute(program, context);
        } break;

        case LETS_BINARY_FUNCTION_RHS: {
            BinaryFunction & fun = pop_binary_function(program);
            auto & lhs_set = pop_set(program, context);
            Ob rhs = pop_ob(program, context);
            lhs_set = fun.get_Rx_set(rhs).raw_data();
            _execute(program, context);
        } break;

        case LETS_SYMMETRIC_FUNCTION_LHS: {
            SymmetricFunction & fun = pop_symmetric_function(program);
            Ob lhs = pop_ob(program, context);
            pop_set(program, context) = fun.get_Lx_set(lhs).raw_data();
            _execute(program, context);
        } break;

        case FOR_NEG: {
            Ob & ob = pop_ob(program, context);
            auto s1 = support().raw_data();
            auto s2 = pop_set(program, context);
            SetIterator<Intersection<1, 1>> iter(item_dim(), {{
                s1, s2
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_NEG_NEG: {
            Ob & ob = pop_ob(program, context);
            auto s1 = support().raw_data();
            auto s2 = pop_set(program, context);
            auto s3 = pop_set(program, context);
            SetIterator<Intersection<1, 2>> iter(item_dim(), {{
                s1, s2, s3
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_POS_NEG: {
            Ob & ob = pop_ob(program, context);
            auto s1 = pop_set(program, context);
            auto s2 = pop_set(program, context);
            SetIterator<Intersection<1, 1>> iter(item_dim(), {{
                s1, s2
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_POS_NEG_NEG: {
            Ob & ob = pop_ob(program, context);
            auto s1 = pop_set(program, context);
            auto s2 = pop_set(program, context);
            auto s3 = pop_set(program, context);
            SetIterator<Intersection<1, 2>> iter(item_dim(), {{
                s1, s2, s3
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_POS_POS: {
            Ob & ob = pop_ob(program, context);
            auto s1 = pop_set(program, context);
            auto s2 = pop_set(program, context);
            SetIterator<Intersection<2>> iter(item_dim(), {{
                s1, s2
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_POS_POS_NEG: {
            Ob & ob = pop_ob(program, context);
            auto s1 = pop_set(program, context);
            auto s2 = pop_set(program, context);
            auto s3 = pop_set(program, context);
            SetIterator<Intersection<2, 1>> iter(item_dim(), {{
                s1, s2, s3
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_POS_POS_NEG_NEG: {
            Ob & ob = pop_ob(program, context);
            auto s1 = pop_set(program, context);
            auto s2 = pop_set(program, context);
            auto s3 = pop_set(program, context);
            auto s4 = pop_set(program, context);
            SetIterator<Intersection<2, 2>> iter(item_dim(), {{
                s1, s2, s3, s4
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_POS_POS_POS: {
            Ob & ob = pop_ob(program, context);
            auto s1 = pop_set(program, context);
            auto s2 = pop_set(program, context);
            auto s3 = pop_set(program, context);
            SetIterator<Intersection<3>> iter(item_dim(), {{
                s1, s2, s3
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_POS_POS_POS_POS: {
            Ob & ob = pop_ob(program, context);
            auto s1 = pop_set(program, context);
            auto s2 = pop_set(program, context);
            auto s3 = pop_set(program, context);
            auto s4 = pop_set(program, context);
            SetIterator<Intersection<4>> iter(item_dim(), {{
                s1, s2, s3, s4
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_POS_POS_POS_POS_POS: {
            Ob & ob = pop_ob(program, context);
            auto s1 = pop_set(program, context);
            auto s2 = pop_set(program, context);
            auto s3 = pop_set(program, context);
            auto s4 = pop_set(program, context);
            auto s5 = pop_set(program, context);
            SetIterator<Intersection<5>> iter(item_dim(), {{
                s1, s2, s3, s4, s5
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_POS_POS_POS_POS_POS_POS: {
            Ob & ob = pop_ob(program, context);
            auto s1 = pop_set(program, context);
            auto s2 = pop_set(program, context);
            auto s3 = pop_set(program, context);
            auto s4 = pop_set(program, context);
            auto s5 = pop_set(program, context);
            auto s6 = pop_set(program, context);
            SetIterator<Intersection<6>> iter(item_dim(), {{
                s1, s2, s3, s4, s5, s6
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_ALL: {
            Ob & ob = pop_ob(program, context);
            for (auto iter = carrier().iter(); iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_UNARY_RELATION: {
            UnaryRelation & rel = pop_unary_relation(program);
            Ob & key = pop_ob(program, context);
            for (auto iter = rel.iter(); iter.ok(); iter.next()) {
                key = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_BINARY_RELATION_LHS: {
            BinaryRelation & rel = pop_binary_relation(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            for (auto iter = rel.iter_lhs(lhs); iter.ok(); iter.next()) {
                rhs = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_BINARY_RELATION_RHS: {
            BinaryRelation & rel = pop_binary_relation(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            for (auto iter = rel.iter_rhs(rhs); iter.ok(); iter.next()) {
                lhs = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_NULLARY_FUNCTION: {
            NullaryFunction & fun = pop_nullary_function(program);
            Ob & val = pop_ob(program, context);
            if (Ob found = fun.find()) {
                val = found;
                _execute(program, context);
            }
        } break;

        case FOR_INJECTIVE_FUNCTION: {
            InjectiveFunction & fun = pop_injective_function(program);
            Ob & key = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            for (auto iter = fun.iter(); iter.ok(); iter.next()) {
                key = *iter;
                val = fun.find(key);
                _execute(program, context);
            }
        } break;

        case FOR_INJECTIVE_FUNCTION_KEY: {
            InjectiveFunction & fun = pop_injective_function(program);
            Ob & key = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            if (Ob found = fun.find(key)) {
                val = found;
                _execute(program, context);
            }
        } break;

        case FOR_INJECTIVE_FUNCTION_VAL: {
            InjectiveFunction & fun = pop_injective_function(program);
            Ob & key = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            if (Ob found = fun.inverse_find(val)) {
                key = found;
                _execute(program, context);
            }
        } break;

        case FOR_BINARY_FUNCTION_LHS: {
            BinaryFunction & fun = pop_binary_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            for (auto iter = fun.iter_lhs(lhs); iter.ok(); iter.next()) {
                rhs = *iter;
                val = fun.find(lhs, rhs);
                _execute(program, context);
            }
        } break;

        case FOR_BINARY_FUNCTION_RHS: {
            BinaryFunction & fun = pop_binary_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            for (auto iter = fun.iter_rhs(rhs); iter.ok(); iter.next()) {
                lhs = *iter;
                val = fun.find(lhs, rhs);
                _execute(program, context);
            }
        } break;

    #if POMAGMA_HAS_INVERSE_INDEX

        case FOR_BINARY_FUNCTION_VAL: {
            BinaryFunction & fun = pop_binary_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            for (auto iter = fun.iter_val(val); iter.ok(); iter.next()) {
                lhs = iter.lhs();
                rhs = iter.rhs();
                _execute(program, context);
            }
        } break;

        case FOR_BINARY_FUNCTION_LHS_VAL: {
            BinaryFunction & fun = pop_binary_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            auto iter = fun.iter_val_lhs(val, lhs);
            for (; iter.ok(); iter.next()) {
                rhs = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_BINARY_FUNCTION_RHS_VAL: {
            BinaryFunction & fun = pop_binary_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            auto iter = fun.iter_val_rhs(val, rhs);
            for (; iter.ok(); iter.next()) {
                lhs = *iter;
                _execute(program, context);
            }
        } break;

    #endif // POMAGMA_HAS_INVERSE_INDEX

        case FOR_BINARY_FUNCTION_LHS_RHS: {
            BinaryFunction & fun = pop_binary_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            if (Ob found = fun.find(lhs, rhs)) {
                val = found;
                _execute(program, context);
            }
        } break;

        case FOR_SYMMETRIC_FUNCTION_LHS: {
            SymmetricFunction & fun = pop_symmetric_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            for (auto iter = fun.iter_lhs(lhs); iter.ok(); iter.next()) {
                rhs = *iter;
                val = fun.find(lhs, rhs);
                _execute(program, context);
            }
        } break;

    #if POMAGMA_HAS_INVERSE_INDEX

        case FOR_SYMMETRIC_FUNCTION_VAL: {
            SymmetricFunction & fun = pop_symmetric_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            for (auto iter = fun.iter_val(val); iter.ok(); iter.next()) {
                lhs = iter.lhs();
                rhs = iter.rhs();
                _execute(program, context);
            }
        } break;

        case FOR_SYMMETRIC_FUNCTION_LHS_VAL: {
            SymmetricFunction & fun = pop_symmetric_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            auto iter = fun.iter_val_lhs(val, lhs);
            for (; iter.ok(); iter.next()) {
                rhs = *iter;
                _execute(program, context);
            }
        } break;

    #endif // POMAGMA_HAS_INVERSE_INDEX

        case FOR_SYMMETRIC_FUNCTION_LHS_RHS: {
            SymmetricFunction & fun = pop_symmetric_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            if (Ob found = fun.find(lhs, rhs)) {
                val = found;
                _execute(program, context);
            }
        } break;

        case FOR_BLOCK: {
            _execute(program, context);
        } break;

        case IF_BLOCK: {
            Ob & ob = pop_ob(program, context);
            if (ob / block_size == context->block) {
                _execute(program, context);
            }
        } break;

        case IF_EQUAL: {
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            if (lhs == rhs) {
                _execute(program, context);
            }
        } break;

        case IF_UNARY_RELATION: {
            UnaryRelation & rel = pop_unary_relation(program);
            Ob & key = pop_ob(program, context);
            if (rel.find(key)) {
                _execute(program, context);
            }
        } break;

        case IF_BINARY_RELATION: {
            BinaryRelation & rel = pop_binary_relation(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            if (rel.find(lhs, rhs)) {
                _execute(program, context);
            }
        } break;

        case IF_NULLARY_FUNCTION: {
            NullaryFunction & fun = pop_nullary_function(program);
            Ob & val = pop_ob(program, context);
            if (fun.find() == val) {
                _execute(program, context);
            }
        } break;

        case IF_INJECTIVE_FUNCTION: {
            InjectiveFunction & fun = pop_injective_function(program);
            Ob & key = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            if (fun.find(key) == val) {
                _execute(program, context);
            }
        } break;

        case IF_BINARY_FUNCTION: {
            BinaryFunction & fun = pop_binary_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            if (fun.find(lhs, rhs) == val) {
                _execute(program, context);
            }
        } break;

        case IF_SYMMETRIC_FUNCTION: {
            SymmetricFunction & fun = pop_symmetric_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            if (fun.find(lhs, rhs) == val) {
                _execute(program, context);
            }
        } break;

        case LET_NULLARY_FUNCTION: {
            NullaryFunction & fun = pop_nullary_function(program);
            Ob & val = pop_ob(program, context);
            val = fun.find();
            POMAGMA_ASSERT1(val, "undefined");
            _execute(program, context);
        } break;

        case LET_INJECTIVE_FUNCTION: {
            InjectiveFunction & fun = pop_injective_function(program);
            Ob & key = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            val = fun.find(key);
            POMAGMA_ASSERT1(val, "undefined");
            _execute(program, context);
        } break;

        case LET_BINARY_FUNCTION: {
            BinaryFunction & fun = pop_binary_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            val = fun.find(lhs, rhs);
            POMAGMA_ASSERT1(val, "undefined");
            _execute(program, context);
        } break;

        case LET_SYMMETRIC_FUNCTION: {
            SymmetricFunction & fun = pop_symmetric_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            val = fun.find(lhs, rhs);
            POMAGMA_ASSERT1(val, "undefined");
            _execute(program, context);
        } break;

        case INFER_EQUAL: {
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            carrier().ensure_equal(lhs, rhs);
        } break;

        case INFER_UNARY_RELATION: {
            UnaryRelation & rel = pop_unary_relation(program);
            Ob & key = pop_ob(program, context);
            rel.insert(key);
        } break;

        case INFER_BINARY_RELATION: {
            BinaryRelation & rel = pop_binary_relation(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            rel.insert(lhs, rhs);
        } break;

        case INFER_NULLARY_FUNCTION: {
            NullaryFunction & fun = pop_nullary_function(program);
            Ob & val = pop_ob(program, context);
            fun.insert(val);
        } break;

        case INFER_INJECTIVE_FUNCTION: {
            InjectiveFunction & fun = pop_injective_function(program);
            Ob & key = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            fun.insert(key, val);
        } break;

        case INFER_BINARY_FUNCTION: {
            BinaryFunction & fun = pop_binary_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & val = pop_ob(program, context);
            fun.insert(lhs, rhs, val);
        } break;

        case INFER_SYMMETRIC_FUNCTION: {
            SymmetricFunction & fun = pop_symmetric_function(program);
            Ob & lhs = pop_ob(program, context);
            Ob & rhs = pop_ob(program, context);
            Ob & key = pop_ob(program, context);
            fun.insert(lhs, rhs, key);
        } break;

        case INFER_NULLARY_NULLARY: {
            auto & fun1 = pop_nullary_function(program);
            auto & fun2 = pop_nullary_function(program);
            if (Ob val = fun1.find()) {
                fun2.insert(val);
            } else if (Ob val = fun2.find()) {
                fun1.insert(val);
            }
        } break;

        case INFER_NULLARY_INJECTIVE: {
            auto & fun1 = pop_nullary_function(program);
            auto & fun2 = pop_injective_function(program);
            auto & key2 = pop_ob(program, context);
            if (Ob val = fun1.find()) {
                fun2.insert(key2, val);
            } else if (Ob val = fun2.find(key2)) {
                fun1.insert(val);
            }
        } break;

        case INFER_NULLARY_BINARY: {
            auto & fun1 = pop_nullary_function(program);
            auto & fun2 = pop_binary_function(program);
            auto & lhs2 = pop_ob(program, context);
            auto & rhs2 = pop_ob(program, context);
            if (Ob val = fun1.find()) {
                fun2.insert(lhs2, rhs2, val);
            } else if (Ob val = fun2.find(lhs2, rhs2)) {
                fun1.insert(val);
            }
        } break;

        case INFER_NULLARY_SYMMETRIC: {
            auto & fun1 = pop_nullary_function(program);
            auto & fun2 = pop_symmetric_function(program);
            auto & lhs2 = pop_ob(program, context);
            auto & rhs2 = pop_ob(program, context);
            if (Ob val = fun1.find()) {
                fun2.insert(lhs2, rhs2, val);
            } else if (Ob val = fun2.find(lhs2, rhs2)) {
                fun1.insert(val);
            }
        } break;

        case INFER_INJECTIVE_INJECTIVE: {
            auto & fun1 = pop_injective_function(program);
            auto & key1 = pop_ob(program, context);
            auto & fun2 = pop_injective_function(program);
            auto & key2 = pop_ob(program, context);
            if (Ob val = fun1.find(key1)) {
                fun2.insert(key2, val);
            } else if (Ob val = fun2.find(key2)) {
                fun1.insert(key1, val);
            }
        } break;

        case INFER_INJECTIVE_BINARY: {
            auto & fun1 = pop_injective_function(program);
            auto & key1 = pop_ob(program, context);
            auto & fun2 = pop_binary_function(program);
            auto & lhs2 = pop_ob(program, context);
            auto & rhs2 = pop_ob(program, context);
            if (Ob val = fun1.find(key1)) {
                fun2.insert(lhs2, rhs2, val);
            } else if (Ob val = fun2.find(lhs2, rhs2)) {
                fun1.insert(key1, val);
            }
        } break;

        case INFER_INJECTIVE_SYMMETRIC: {
            auto & fun1 = pop_injective_function(program);
            auto & key1 = pop_ob(program, context);
            auto & fun2 = pop_symmetric_function(program);
            auto & lhs2 = pop_ob(program, context);
            auto & rhs2 = pop_ob(program, context);
            if (Ob val = fun1.find(key1)) {
                fun2.insert(lhs2, rhs2, val);
            } else if (Ob val = fun2.find(lhs2, rhs2)) {
                fun1.insert(key1, val);
            }
        } break;

        case INFER_BINARY_BINARY: {
            auto & fun1 = pop_binary_function(program);
            auto & lhs1 = pop_ob(program, context);
            auto & rhs1 = pop_ob(program, context);
            auto & fun2 = pop_binary_function(program);
            auto & lhs2 = pop_ob(program, context);
            auto & rhs2 = pop_ob(program, context);
            if (Ob val = fun1.find(lhs1, rhs1)) {
                fun2.insert(lhs2, rhs2, val);
            } else if (Ob val = fun2.find(lhs2, rhs2)) {
                fun1.insert(lhs1, rhs1, val);
            }
        } break;

        case INFER_BINARY_SYMMETRIC: {
            auto & fun1 = pop_binary_function(program);
            auto & lhs1 = pop_ob(program, context);
            auto & rhs1 = pop_ob(program, context);
            auto & fun2 = pop_symmetric_function(program);
            auto & lhs2 = pop_ob(program, context);
            auto & rhs2 = pop_ob(program, context);
            if (Ob val = fun1.find(lhs1, rhs1)) {
                fun2.insert(lhs2, rhs2, val);
            } else if (Ob val = fun2.find(lhs2, rhs2)) {
                fun1.insert(lhs1, rhs1, val);
            }
        } break;

        case INFER_SYMMETRIC_SYMMETRIC: {
            auto & fun1 = pop_symmetric_function(program);
            auto & lhs1 = pop_ob(program, context);
            auto & rhs1 = pop_ob(program, context);
            auto & fun2 = pop_symmetric_function(program);
            auto & lhs2 = pop_ob(program, context);
            auto & rhs2 = pop_ob(program, context);
            if (Ob val = fun1.find(lhs1, rhs1)) {
                fun2.insert(lhs2, rhs2, val);
            } else if (Ob val = fun2.find(lhs2, rhs2)) {
                fun1.insert(lhs1, rhs1, val);
            }
        } break;

    #if not POMAGMA_HAS_INVERSE_INDEX

        case FOR_BINARY_FUNCTION_VAL:
        case FOR_BINARY_FUNCTION_LHS_VAL:
        case FOR_BINARY_FUNCTION_RHS_VAL:
        case FOR_SYMMETRIC_FUNCTION_VAL:
        case FOR_SYMMETRIC_FUNCTION_LHS_VAL: {
            POMAGMA_ERROR(g_op_code_names[op_code] << " is not supported");
        } break;

    #endif // POMAGMA_HAS_INVERSE_INDEX
    }

    if (POMAGMA_TRACE_VM) {
        --context->trace;
    }
}

//----------------------------------------------------------------------------
// Agenda

template<class T>
static void register_names (
        std::map<std::string, const void *> & names,
        const std::unordered_map<std::string, T *> objects)
{
    for (const auto & pair : objects) {
        names[pair.first] = static_cast<const void *>(pair.second);
    }
}

void Agenda::load (Signature & signature)
{
    m_virtual_machine.load(signature);
    m_block_count =
        signature.carrier()->item_dim() / VirtualMachine::block_size + 1;

    m_names.clear();
    register_names(m_names, signature.unary_relations());
    register_names(m_names, signature.binary_relations());
    register_names(m_names, signature.nullary_functions());
    register_names(m_names, signature.injective_functions());
    register_names(m_names, signature.binary_functions());
    register_names(m_names, signature.symmetric_functions());
}

inline void Agenda::add_program_to (
        Programs & programs,
        Program program,
        size_t size,
        size_t lineno)
{
    programs.push_back(program);
    m_sizes[program] = size;
    m_linenos[program] = lineno;
}

void Agenda::add_listing (const ProgramParser & parser, const Listing & listing)
{
    Program program = parser.find_program(listing);
    const size_t size = listing.size;
    const size_t lineno = listing.lineno;

    POMAGMA_ASSERT(size, "empty program");
    OpCode op_code = static_cast<OpCode>(program[0]);

    const size_t skip = 1 + g_op_code_arities[op_code].size();
    POMAGMA_ASSERT_LT(skip, size);
    Program truncated = program + skip;
    const size_t trunc_size = size - skip;

    switch (op_code) {
        case GIVEN_EXISTS: {
            add_program_to(m_exists, truncated, trunc_size, lineno);
        } break;

        case GIVEN_UNARY_RELATION: {
            auto ptr = m_virtual_machine.unary_relation(program[1]);
            add_program_to(m_structures[ptr], truncated, trunc_size, lineno);
        } break;

        case GIVEN_BINARY_RELATION: {
            auto ptr = m_virtual_machine.binary_relation(program[1]);
            add_program_to(m_structures[ptr], truncated, trunc_size, lineno);
        } break;

        case GIVEN_NULLARY_FUNCTION: {
            auto ptr = m_virtual_machine.nullary_function(program[1]);
            add_program_to(m_structures[ptr], truncated, trunc_size, lineno);
        } break;

        case GIVEN_INJECTIVE_FUNCTION: {
            auto ptr = m_virtual_machine.injective_function(program[1]);
            add_program_to(m_structures[ptr], truncated, trunc_size, lineno);
        } break;

        case GIVEN_BINARY_FUNCTION: {
            auto ptr = m_virtual_machine.binary_function(program[1]);
            add_program_to(m_structures[ptr], truncated, trunc_size, lineno);
        } break;

        case GIVEN_SYMMETRIC_FUNCTION: {
            auto ptr = m_virtual_machine.symmetric_function(program[1]);
            add_program_to(m_structures[ptr], truncated, trunc_size, lineno);
        } break;

        case FOR_BLOCK: {
            add_program_to(m_cleanup_large, program, trunc_size, lineno);
        } break;

        default: {
            add_program_to(m_cleanup_small, program, size, lineno);
        } break;
    }
}

size_t Agenda::count_bytes (const Programs & programs) const
{
    size_t byte_count = 0;
    for (Program program : programs) {
        byte_count += map_find(m_sizes, program);
    }
    return byte_count;
}

void Agenda::log_stats () const
{
    POMAGMA_INFO("Agenda:");
    POMAGMA_INFO("\tEvent\tCount\tTotal bytes");
    POMAGMA_INFO("\t---------------------------");
    POMAGMA_INFO(
        "\tExists" <<
        "\t" << m_exists.size() <<
        "\t" << count_bytes(m_exists));
    for (const auto & pair : m_names) {
        auto i = m_structures.find(pair.second);
        if (i != m_structures.end()) {
            const auto & programs = i->second;
            POMAGMA_INFO(
                "\t" << pair.first <<
                "\t" << programs.size() <<
                "\t" << count_bytes(programs));
        }
    }
    POMAGMA_INFO(
        "\tCleanup" <<
        "\t" << m_cleanup_small.size() <<
        "\t" << count_bytes(m_cleanup_small));
    POMAGMA_INFO(
        "\tCleanup" <<
        "\t" << m_cleanup_large.size() <<
        "\t" << count_bytes(m_cleanup_large));
}

} // namespace vm
} // namespace pomagma
