#include "vm.hpp"

namespace pomagma
{
namespace vm
{

void VirtualMachine::execute (const Operation * program)
{
    const Operation & op = program[0];
    const uint8_t * args = op.args();
    switch (op.op_code()) {

        case IF_EQUAL: {
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            if (lhs == rhs) {
                execute(program + 1);
            }
        } break;

        case IF_UNARY_RELATION: {
            UnaryRelation & rel = pop_unary_relation(args);
            Ob & key = pop_ob(args);
            if (rel.find(key)) {
                execute(program + 1);
            }
        } break;

        case IF_BINARY_RELATION: {
            BinaryRelation & rel = pop_binary_relation(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            if (rel.find(lhs, rhs)) {
                execute(program + 1);
            }
        } break;

        case FOR_ALL: {
            Ob & ob = pop_ob(args);
            for (auto iter = carrier().iter(); iter.ok(); iter.next()) {
                ob = *iter;
                execute(program + 1);
            }
        } break;

        case FOR_UNARY_RELATION: {
            UnaryRelation & rel = pop_unary_relation(args);
            Ob & key = pop_ob(args);
            for (auto iter = rel.iter(); iter.ok(); iter.next()) {
                key = *iter;
                execute(program + 1);
            }
        } break;

        case FOR_BINARY_RELATION_LHS: {
            BinaryRelation & rel = pop_binary_relation(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            for (auto iter = rel.iter_lhs(lhs); iter.ok(); iter.next()) {
                rhs = *iter;
                execute(program + 1);
            }
        } break;

        case FOR_BINARY_RELATION_RHS: {
            BinaryRelation & rel = pop_binary_relation(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            for (auto iter = rel.iter_rhs(rhs); iter.ok(); iter.next()) {
                lhs = *iter;
                execute(program + 1);
            }
        } break;

        case FOR_NULLARY_FUNCTION: {
            NullaryFunction & fun = pop_nullary_function(args);
            if (Ob val = fun.find()) {
                pop_ob(args) = val;
                execute(program + 1);
            }
        } break;

        case FOR_INJECTIVE_FUNCTION: {
            InjectiveFunction & fun = pop_injective_function(args);
            Ob & key = pop_ob(args);
            Ob & val = pop_ob(args);
            for (auto iter = fun.iter(); iter.ok(); iter.next()) {
                key = *iter;
                val = fun.find(key);
                execute(program + 1);
            }
        } break;

        case FOR_INJECTIVE_FUNCTION_KEY: {
            InjectiveFunction & fun = pop_injective_function(args);
            Ob & key = pop_ob(args);
            if (Ob val = fun.find(key)) {
                pop_ob(args) = val;
                execute(program + 1);
            }
        } break;

        case FOR_INJECTIVE_FUNCTION_VAL: {
            InjectiveFunction & fun = pop_injective_function(args);
            Ob & val = pop_ob(args);
            if (Ob key = fun.inverse_find(val)) {
                pop_ob(args) = key;
                execute(program + 1);
            }
        } break;

        case FOR_BINARY_FUNCTION_LHS: {
            BinaryFunction & fun = pop_binary_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            Ob & val = pop_ob(args);
            for (auto iter = fun.iter_lhs(lhs); iter.ok(); iter.next()) {
                rhs = *iter;
                val = fun.find(lhs, rhs);
                execute(program + 1);
            }
        } break;

        case FOR_BINARY_FUNCTION_RHS: {
            BinaryFunction & fun = pop_binary_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            Ob & val = pop_ob(args);
            for (auto iter = fun.iter_rhs(rhs); iter.ok(); iter.next()) {
                lhs = *iter;
                val = fun.find(lhs, rhs);
                execute(program + 1);
            }
        } break;

        case FOR_BINARY_FUNCTION_VAL: {
            BinaryFunction & fun = pop_binary_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            Ob & val = pop_ob(args);
            for (auto iter = fun.iter_val(val); iter.ok(); iter.next()) {
                lhs = iter.lhs();
                rhs = iter.rhs();
                execute(program + 1);
            }
        } break;

        case FOR_BINARY_FUNCTION_LHS_VAL: {
            BinaryFunction & fun = pop_binary_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            Ob & val = pop_ob(args);
            auto iter = fun.iter_val_lhs(val, lhs);
            for (; iter.ok(); iter.next()) {
                rhs = *iter;
                execute(program + 1);
            }
        } break;

        case FOR_BINARY_FUNCTION_RHS_VAL: {
            BinaryFunction & fun = pop_binary_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            Ob & val = pop_ob(args);
            auto iter = fun.iter_val_rhs(val, rhs);
            for (; iter.ok(); iter.next()) {
                lhs = *iter;
                execute(program + 1);
            }
        } break;

        case FOR_BINARY_FUNCTION_LHS_RHS: {
            BinaryFunction & fun = pop_binary_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            if (Ob val = fun.find(lhs, rhs)) {
                pop_ob(args) = val;
                execute(program + 1);
            }
        } break;

        case FOR_SYMMETRIC_FUNCTION_LHS: {
            SymmetricFunction & fun = pop_symmetric_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            Ob & val = pop_ob(args);
            for (auto iter = fun.iter_lhs(lhs); iter.ok(); iter.next()) {
                rhs = *iter;
                val = fun.find(lhs, rhs);
                execute(program + 1);
            }
        } break;

        case FOR_SYMMETRIC_FUNCTION_VAL: {
            SymmetricFunction & fun = pop_symmetric_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            Ob & val = pop_ob(args);
            for (auto iter = fun.iter_val(val); iter.ok(); iter.next()) {
                lhs = iter.lhs();
                rhs = iter.rhs();
                execute(program + 1);
            }
        } break;

        case FOR_SYMMETRIC_FUNCTION_LHS_VAL: {
            SymmetricFunction & fun = pop_symmetric_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            Ob & val = pop_ob(args);
            auto iter = fun.iter_val_lhs(val, lhs);
            for (; iter.ok(); iter.next()) {
                rhs = *iter;
                execute(program + 1);
            }
        } break;

        case FOR_SYMMETRIC_FUNCTION_LHS_RHS: {
            SymmetricFunction & fun = pop_symmetric_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            if (Ob val = fun.find(lhs, rhs)) {
                pop_ob(args) = val;
                execute(program + 1);
            }
        } break;

        case ENSURE_EQUAL: {
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            carrier().ensure_equal(lhs, rhs);
        } break;

        case ENSURE_UNARY_RELATION: {
            UnaryRelation & rel = pop_unary_relation(args);
            Ob & key = pop_ob(args);
            rel.insert(key);
        } break;

        case ENSURE_BINARY_RELATION: {
            BinaryRelation & rel = pop_binary_relation(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            rel.insert(lhs, rhs);
        } break;

        case ENSURE_INJECTIVE_FUNCTION: {
            InjectiveFunction & fun = pop_injective_function(args);
            Ob & key = pop_ob(args);
            Ob & val = pop_ob(args);
            fun.insert(key, val);
        } break;

        case ENSURE_BINARY_FUNCTION: {
            BinaryFunction & fun = pop_binary_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            Ob & val = pop_ob(args);
            fun.insert(lhs, rhs, val);
        } break;

        case ENSURE_SYMMETRIC_FUNCTION: {
            SymmetricFunction & fun = pop_symmetric_function(args);
            Ob & lhs = pop_ob(args);
            Ob & rhs = pop_ob(args);
            Ob & key = pop_ob(args);
            fun.insert(lhs, rhs, key);
        } break;

        case ENSURE_COMPOUND: {
            auto for_ensure1 = program + 1;
            auto for_ensure2 = program + 3;
            Ob & ob = pop_ob(args);
            ob = 0;
            execute(for_ensure1);
            if (not ob) {
                execute(for_ensure2);
            }
        } break;
    }
}

} // namespace vm
} // namespace pomagma
