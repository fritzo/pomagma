#include <map>
#include <typeinfo>
#include <sstream>
#include "vm.hpp"

namespace pomagma
{
namespace vm
{

//----------------------------------------------------------------------------
// OpCode

enum OpArgType {
    OB,
    SET,
    UNARY_RELATION,
    BINARY_RELATION,
    NULLARY_FUNCTION,
    INJECTIVE_FUNCTION,
    BINARY_FUNCTION,
    SYMMETRIC_FUNCTION,
};

#define OP_CODES(DO) \
    DO(IF_EQUAL, ({OB, OB})) \
    DO(IF_UNARY_RELATION, ({UNARY_RELATION, OB})) \
    DO(IF_BINARY_RELATION, ({BINARY_RELATION, OB, OB})) \
    DO(SET_UNARY_RELATION, ({UNARY_RELATION, SET})) \
    DO(SET_BINARY_RELATION_LHS, ({BINARY_RELATION, OB, SET})) \
    DO(SET_BINARY_RELATION_RHS, ({BINARY_RELATION, OB, SET})) \
    DO(SET_INJECTIVE_FUNCTION, ({INJECTIVE_FUNCTION, SET})) \
    DO(SET_INJECTIVE_FUNCTION_INVERSE, ({INJECTIVE_FUNCTION, SET})) \
    DO(SET_BINARY_FUNCTION_LHS, ({BINARY_FUNCTION, OB, SET})) \
    DO(SET_BINARY_FUNCTION_RHS, ({BINARY_FUNCTION, OB, SET})) \
    DO(SET_SYMMETRIC_FUNCTION_LHS, ({SYMMETRIC_FUNCTION, OB, SET})) \
    DO(FOR_INTERSECTION_2, ({OB, SET, SET})) \
    DO(FOR_INTERSECTION_3, ({OB, SET, SET, SET})) \
    DO(FOR_INTERSECTION_4, ({OB, SET, SET, SET, SET})) \
    DO(FOR_INTERSECTION_5, ({OB, SET, SET, SET, SET, SET})) \
    DO(FOR_INTERSECTION_6, ({OB, SET, SET, SET, SET, SET, SET})) \
    DO(FOR_ALL, ({OB})) \
    DO(FOR_UNARY_RELATION, ({UNARY_RELATION, OB})) \
    DO(FOR_BINARY_RELATION_LHS, ({BINARY_RELATION, OB, OB})) \
    DO(FOR_BINARY_RELATION_RHS, ({BINARY_RELATION, OB, OB})) \
    DO(FOR_NULLARY_FUNCTION, ({NULLARY_FUNCTION, OB})) \
    DO(FOR_INJECTIVE_FUNCTION, ({INJECTIVE_FUNCTION, OB, OB})) \
    DO(FOR_INJECTIVE_FUNCTION_KEY, ({INJECTIVE_FUNCTION, OB, OB})) \
    DO(FOR_INJECTIVE_FUNCTION_VAL, ({INJECTIVE_FUNCTION, OB, OB})) \
    DO(FOR_BINARY_FUNCTION_LHS, ({BINARY_FUNCTION, OB, OB, OB})) \
    DO(FOR_BINARY_FUNCTION_RHS, ({BINARY_FUNCTION, OB, OB, OB})) \
    DO(FOR_BINARY_FUNCTION_VAL, ({BINARY_FUNCTION, OB, OB, OB})) \
    DO(FOR_BINARY_FUNCTION_LHS_VAL, ({BINARY_FUNCTION, OB, OB, OB})) \
    DO(FOR_BINARY_FUNCTION_RHS_VAL, ({BINARY_FUNCTION, OB, OB, OB})) \
    DO(FOR_BINARY_FUNCTION_LHS_RHS, ({BINARY_FUNCTION, OB, OB, OB})) \
    DO(FOR_SYMMETRIC_FUNCTION_LHS, ({SYMMETRIC_FUNCTION, OB, OB, OB})) \
    DO(FOR_SYMMETRIC_FUNCTION_VAL, ({SYMMETRIC_FUNCTION, OB, OB, OB})) \
    DO(FOR_SYMMETRIC_FUNCTION_LHS_VAL, ({SYMMETRIC_FUNCTION, OB, OB, OB})) \
    DO(FOR_SYMMETRIC_FUNCTION_LHS_RHS, ({SYMMETRIC_FUNCTION, OB, OB, OB})) \
    DO(ENSURE_EQUAL, ({OB, OB})) \
    DO(ENSURE_UNARY_RELATION, ({OB})) \
    DO(ENSURE_BINARY_RELATION, ({OB, OB})) \
    DO(ENSURE_INJECTIVE_FUNCTION, ({INJECTIVE_FUNCTION, OB, OB})) \
    DO(ENSURE_BINARY_FUNCTION, ({BINARY_FUNCTION, OB, OB, OB})) \
    DO(ENSURE_SYMMETRIC_FUNCTION, ({SYMMETRIC_FUNCTION, OB, OB, OB})) \
    DO(ENSURE_COMPOUND, ({OB}))

enum OpCode : uint8_t
{
#define DO(X, Y) X,
    OP_CODES(DO)
#undef DO
};

static const std::string g_op_code_names[] =
{
#define DO(X, Y) #X,
    OP_CODES(DO)
#undef DO
};

static std::vector<std::vector<OpArgType>> get_op_code_arities ()
{
    std::vector<std::vector<OpArgType>> result = {
#define DO(X, Y) std::vector<OpArgType> Y,
        OP_CODES(DO)
#undef DO
    };
    return result;
}

static const std::vector<std::vector<OpArgType>> g_op_code_arities =
    get_op_code_arities();

#undef OP_CODES

static const size_t g_op_code_count =
    sizeof(g_op_code_names) / sizeof(std::string);

//----------------------------------------------------------------------------
// Parser

template<class Table>
static void declare (
        const std::unordered_map<std::string, Table *> & pointers,
        std::unordered_map<std::string, uint8_t> & vm_pointers)
{
    POMAGMA_ASSERT(
        pointers.size() <= 256,
        "too many " << demangle(typeid(Table).name()) << " symbols: "
        "expected <= 256, actual = " << pointers.size());

    vm_pointers.clear();

    std::map<std::string, Table *> sorted;
    sorted.insert(pointers.begin(), pointers.end());
    uint8_t vm_pointer = 0;
    for (auto pair : sorted) {
        vm_pointers[pair.first] = vm_pointer++;
    }
}

Parser::Parser (Signature & signature)
{
    for (size_t op_code = 0; op_code < g_op_code_count; ++op_code) {
        m_op_codes[g_op_code_names[op_code]] = static_cast<OpCode>(op_code);
    }

    declare(signature.unary_relations(), m_unary_relations);
    declare(signature.binary_relations(), m_binary_relations);
    declare(signature.nullary_functions(), m_nullary_functions);
    declare(signature.injective_functions(), m_injective_functions);
    declare(signature.binary_functions(), m_binary_functions);
    declare(signature.symmetric_functions(), m_symmetric_functions);
}

std::vector<std::vector<Operation>> Parser::parse (std::istream & infile) const
{
    std::vector<std::vector<Operation>> programs;
    std::vector<Operation> program;
    SymbolTable obs;
    SymbolTable sets;
    std::string line;
    std::string word;

    for (int lineno = 0; std::getline(infile, line); ++lineno) {
        if (line[0] == '#') {
            continue;
        }
        if (line.empty()) {
            obs.clear();
            sets.clear();
            if (not program.empty()) {
                programs.push_back(program);
                program.clear();
            }
            continue;
        }

        std::istringstream stream(line);

        POMAGMA_ASSERT(
            stream >> word,
            "line " << lineno << ": no operation");
        auto i = m_op_codes.find(word);
        POMAGMA_ASSERT(
            i != m_op_codes.end(),
            "line " << lineno << ": unknown operation: " << word);
        Operation operation = {{i->second, 0, 0, 0, 0, 0, 0, 0}};

        uint8_t * args = operation.args();
        for (auto arg_type : g_op_code_arities[operation.op_code()]) {

            POMAGMA_ASSERT(
                stream >> word,
                "line " << lineno << ": too few arguments");

            switch (arg_type) {
                case OB: {
                    *args++ = obs(word);
                } break;

                case SET: {
                    *args++ = sets(word);
                } break;

                case UNARY_RELATION: {
                    *args++ = m_unary_relations.find(word)->second;
                } break;

                case BINARY_RELATION: {
                    *args++ = m_binary_relations.find(word)->second;
                } break;

                case NULLARY_FUNCTION: {
                    *args++ = m_injective_functions.find(word)->second;
                } break;

                case INJECTIVE_FUNCTION: {
                    *args++ = m_injective_functions.find(word)->second;
                } break;

                case BINARY_FUNCTION: {
                    *args++ = m_binary_functions.find(word)->second;
                } break;

                case SYMMETRIC_FUNCTION: {
                    *args++ = m_symmetric_functions.find(word)->second;
                } break;
            }
        }

        POMAGMA_ASSERT(
            not (stream >> word),
            "line " << lineno << ": too many arguments: " << word);

        program.push_back(operation);
    }

    if (not program.empty()) {
        programs.push_back(program);
    }

    return programs;
}

//----------------------------------------------------------------------------
// VirtualMachine

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

VirtualMachine::VirtualMachine (Signature & signature)
    : m_carrier(* signature.carrier())
{
    POMAGMA_ASSERT(is_aligned(this, 64), "VirtualMachine is misaligned");

    for (size_t i = 0; i < 256; ++i) {
        m_obs[i] = 0;
        m_sets[i] = nullptr;
    }

    declare(signature.unary_relations(), m_unary_relations);
    declare(signature.binary_relations(), m_binary_relations);
    declare(signature.nullary_functions(), m_nullary_functions);
    declare(signature.injective_functions(), m_injective_functions);
    declare(signature.binary_functions(), m_binary_functions);
    declare(signature.symmetric_functions(), m_symmetric_functions);
}

void VirtualMachine::execute (const Operation * program)
{
    POMAGMA_ASSERT5(is_aligned(program, 8), "program is misaligned");

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

        case SET_UNARY_RELATION: {
            UnaryRelation & rel = pop_unary_relation(args);
            pop_set(args) = rel.get_set().raw_data();
        } break;

        case SET_BINARY_RELATION_LHS: {
            BinaryRelation & rel = pop_binary_relation(args);
            Ob lhs = pop_ob(args);
            pop_set(args) = rel.get_Lx_set(lhs).raw_data();
        } break;

        case SET_BINARY_RELATION_RHS: {
            BinaryRelation & rel = pop_binary_relation(args);
            Ob rhs = pop_ob(args);
            pop_set(args) = rel.get_Rx_set(rhs).raw_data();
        } break;

        case SET_INJECTIVE_FUNCTION: {
            InjectiveFunction & fun = pop_injective_function(args);
            pop_set(args) = fun.defined().raw_data();
        } break;

        case SET_INJECTIVE_FUNCTION_INVERSE: {
            InjectiveFunction & fun = pop_injective_function(args);
            pop_set(args) = fun.defined().raw_data();
        } break;

        case SET_BINARY_FUNCTION_LHS: {
            BinaryFunction & fun = pop_binary_function(args);
            Ob lhs = pop_ob(args);
            pop_set(args) = fun.get_Lx_set(lhs).raw_data();
        } break;

        case SET_BINARY_FUNCTION_RHS: {
            BinaryFunction & fun = pop_binary_function(args);
            Ob rhs = pop_ob(args);
            pop_set(args) = fun.get_Rx_set(rhs).raw_data();
        } break;

        case SET_SYMMETRIC_FUNCTION_LHS: {
            SymmetricFunction & fun = pop_symmetric_function(args);
            Ob lhs = pop_ob(args);
            pop_set(args) = fun.get_Lx_set(lhs).raw_data();
        } break;

        case FOR_INTERSECTION_2: {
            Ob & ob = pop_ob(args);
            SetIterator<2> iter(item_dim(), {{
                m_sets[args[0]],
                m_sets[args[1]],
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                execute(program + 1);
            }
        } break;

        case FOR_INTERSECTION_3: {
            Ob & ob = pop_ob(args);
            SetIterator<3> iter(item_dim(), {{
                m_sets[args[0]],
                m_sets[args[1]],
                m_sets[args[2]],
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                execute(program + 1);
            }
        } break;

        case FOR_INTERSECTION_4: {
            Ob & ob = pop_ob(args);
            SetIterator<4> iter(item_dim(), {{
                m_sets[args[0]],
                m_sets[args[1]],
                m_sets[args[2]],
                m_sets[args[3]],
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                execute(program + 1);
            }
        } break;

        case FOR_INTERSECTION_5: {
            Ob & ob = pop_ob(args);
            SetIterator<5> iter(item_dim(), {{
                m_sets[args[0]],
                m_sets[args[1]],
                m_sets[args[2]],
                m_sets[args[3]],
                m_sets[args[4]],
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                execute(program + 1);
            }
        } break;

        case FOR_INTERSECTION_6: {
            Ob & ob = pop_ob(args);
            SetIterator<6> iter(item_dim(), {{
                m_sets[args[0]],
                m_sets[args[1]],
                m_sets[args[2]],
                m_sets[args[3]],
                m_sets[args[4]],
                m_sets[args[5]],
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
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
