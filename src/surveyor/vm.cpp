#include <map>
#include <unordered_set>
#include <typeinfo>
#include <sstream>
#include <fstream>
#include "vm.hpp"

#define POMAGMA_TRACE_VM (false)

namespace pomagma
{
namespace vm
{

//----------------------------------------------------------------------------
// OpCode

enum OpArgType : uint8_t
{
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

#define OP_CODES(DO) \
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
    DO(FOR_POS_POS, ({NEW_OB, SET, SET})) \
    DO(FOR_POS_POS_POS, ({NEW_OB, SET, SET, SET})) \
    DO(FOR_POS_POS_POS_POS, ({NEW_OB, SET, SET, SET, SET})) \
    DO(FOR_POS_POS_POS_POS_POS, ({NEW_OB, SET, SET, SET, SET, SET})) \
    DO(FOR_POS_POS_POS_POS_POS_POS, ({NEW_OB, SET, SET, SET, SET, SET, SET})) \
    DO(FOR_POS_NEG, ({NEW_OB, SET, SET})) \
    DO(FOR_POS_NEG_NEG, ({NEW_OB, SET, SET, SET})) \
    DO(FOR_NEG, ({NEW_OB, SET})) \
    DO(FOR_NEG_NEG, ({NEW_OB, SET, SET})) \
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
    OP_CODES(DO)
#undef DO
};

static const std::string g_op_code_names[] =
{
#define DO(X, Y) #X,
    OP_CODES(DO)
#undef DO
};

inline std::vector<std::vector<OpArgType>> get_op_code_arities ()
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

class Parser::SymbolTable
{
    std::unordered_map<std::string, uint8_t> m_registers;
    std::unordered_set<std::string> m_loaded;

public:

    void clear () { m_registers.clear(); }

    uint8_t store (const std::string & name, size_t lineno)
    {
        POMAGMA_ASSERT(
            m_registers.find(name) == m_registers.end(),
            "line " << lineno << ": duplicate variable: " << name);
        POMAGMA_ASSERT(
            m_registers.size() < 256,
            "line " << lineno << ": too many variables, limit = 256");

        uint8_t index = m_registers.size();
        m_registers.insert(std::make_pair(name, index));
        return index;
    }

    uint8_t load (const std::string & name, size_t lineno)
    {
        auto i = m_registers.find(name);
        POMAGMA_ASSERT(
            i != m_registers.end(),
            "line " << lineno << ": undefined variable: " << name);
        m_loaded.insert(name);
        return i->second;
    }

    void check_unused (size_t lineno) const
    {
        for (const auto & pair : m_registers) {
            const std::string & name = pair.first;
            POMAGMA_ASSERT(
                m_loaded.find(name) != m_loaded.end(),
                "line " << lineno << ": unused variable: " << name);
        }
    }
};


template<class Table>
static void declare (
        OpArgType arity,
        const std::unordered_map<std::string, Table *> & pointers,
        std::map<std::pair<OpArgType, std::string>, uint8_t> & symbols)
{
    POMAGMA_ASSERT(
        pointers.size() <= 256,
        "too many " << demangle(typeid(Table).name()) << " symbols: "
        "expected <= 256, actual = " << pointers.size());

    std::map<std::string, Table *> sorted;
    sorted.insert(pointers.begin(), pointers.end());
    uint8_t vm_pointer = 0;
    for (auto pair : sorted) {
        symbols[std::make_pair(arity, pair.first)] = vm_pointer++;
    }
}

Parser::Parser (Signature & signature)
{
    POMAGMA_DEBUG("Op Codes:");
    for (size_t op_code = 0; op_code < g_op_code_count; ++op_code) {
        m_op_codes[g_op_code_names[op_code]] = static_cast<OpCode>(op_code);
        POMAGMA_DEBUG(g_op_code_names[op_code] << " = " << op_code);
    }

    m_constants.clear();
    declare(UNARY_RELATION, signature.unary_relations(), m_constants);
    declare(BINARY_RELATION, signature.binary_relations(), m_constants);
    declare(NULLARY_FUNCTION, signature.nullary_functions(), m_constants);
    declare(INJECTIVE_FUNCTION, signature.injective_functions(), m_constants);
    declare(BINARY_FUNCTION, signature.binary_functions(), m_constants);
    declare(SYMMETRIC_FUNCTION, signature.symmetric_functions(), m_constants);
}

std::vector<std::vector<uint8_t>> Parser::parse_file (
        const std::string & filename) const
{
    POMAGMA_INFO("loading programs from " << filename);
    std::ifstream infile(filename, std::ifstream::in | std::ifstream::binary);
    POMAGMA_ASSERT(infile.is_open(), "failed to open file: " << filename);
    return parse(infile);
}

std::vector<std::vector<uint8_t>> Parser::parse (std::istream & infile) const
{
    std::vector<std::vector<uint8_t>> programs;
    std::vector<uint8_t> program;
    SymbolTable obs;
    SymbolTable sets;
    std::string line;
    std::string word;

    for (int lineno = 1; std::getline(infile, line); ++lineno) {
        if (line.size() and line[0] == '#') {
            continue;
        }
        if (line.empty()) {
            sets.check_unused(lineno);
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
        OpCode op_code = i->second;
        program.push_back(op_code);

        for (auto arg_type : g_op_code_arities[op_code]) {

            POMAGMA_ASSERT(
                stream >> word,
                "line " << lineno << ": too few arguments");

            uint8_t arg = 0xff;
            switch (arg_type) {
                case NEW_OB: {
                    arg = obs.store(word, lineno);
                } break;

                case OB: {
                    arg = obs.load(word, lineno);
                } break;

                case NEW_SET: {
                    arg = sets.store(word, lineno);
                } break;

                case SET: {
                    arg = sets.load(word, lineno);
                } break;

                default: {
                    auto i = m_constants.find(std::make_pair(arg_type, word));
                    POMAGMA_ASSERT(
                        i != m_constants.end(),
                        "line " << lineno << ": unknown constant: " << word);
                    arg = i->second;
                } break;
            }
            program.push_back(arg);
        }

        POMAGMA_ASSERT(
            not (stream >> word),
            "line " << lineno << ": too many arguments: " << word);
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
    if (POMAGMA_TRACE_VM) {
        POMAGMA_ASSERT_LE(context->trace, 256);
        POMAGMA_DEBUG(
            (spaces_256 + 256 - context->trace) <<
            g_op_code_names[program[0]]);
        ++context->trace;
    }

    switch (pop_op_code(program)) {

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

        case FOR_POS_NEG: {
            Ob & ob = pop_ob(program, context);
            const std::atomic<Word> * s1 = pop_set(program, context);
            const std::atomic<Word> * s2 = pop_set(program, context);
            SetIterator<Intersection<2, true>> iter(item_dim(), {{
                s1, s2
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_POS_NEG_NEG: {
            Ob & ob = pop_ob(program, context);
            const std::atomic<Word> * s1 = pop_set(program, context);
            const std::atomic<Word> * s2 = pop_set(program, context);
            const std::atomic<Word> * s3 = pop_set(program, context);
            SetIterator<Intersection<3, true>> iter(item_dim(), {{
                s1, s2, s3
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_NEG: {
            Ob & ob = pop_ob(program, context);
            const std::atomic<Word> * s1 = support().raw_data();
            const std::atomic<Word> * s2 = pop_set(program, context);
            SetIterator<Intersection<2, true>> iter(item_dim(), {{
                s1, s2
            }});
            for (; iter.ok(); iter.next()) {
                ob = *iter;
                _execute(program, context);
            }
        } break;

        case FOR_NEG_NEG: {
            Ob & ob = pop_ob(program, context);
            const std::atomic<Word> * s1 = support().raw_data();
            const std::atomic<Word> * s2 = pop_set(program, context);
            const std::atomic<Word> * s3 = pop_set(program, context);
            SetIterator<Intersection<3, true>> iter(item_dim(), {{
                s1, s2, s3
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
    }

    if (POMAGMA_TRACE_VM) {
        --context->trace;
    }
}

//----------------------------------------------------------------------------
// Agenda

void Agenda::add_listing (const Listing & listing)
{
    POMAGMA_ASSERT(not listing.empty(), "empty listing");
    OpCode op_code = static_cast<OpCode>(listing[0]);

    size_t skip = 1 + g_op_code_arities[op_code].size();
    Listing truncated(listing.begin() + skip, listing.end());

    switch (op_code) {
        case GIVEN_EXISTS: {
            m_exists.push_back(truncated);
        } break;

        case GIVEN_UNARY_RELATION: {
            auto ptr = m_virtual_machine.unary_relation(listing[1]);
            m_unary_relations[ptr].push_back(truncated);
        } break;

        case GIVEN_BINARY_RELATION: {
            auto ptr = m_virtual_machine.binary_relation(listing[1]);
            m_binary_relations[ptr].push_back(truncated);
        } break;

        case GIVEN_NULLARY_FUNCTION: {
            auto ptr = m_virtual_machine.nullary_function(listing[1]);
            m_nullary_functions[ptr].push_back(truncated);
        } break;

        case GIVEN_INJECTIVE_FUNCTION: {
            auto ptr = m_virtual_machine.injective_function(listing[1]);
            m_injective_functions[ptr].push_back(truncated);
        } break;

        case GIVEN_BINARY_FUNCTION: {
            auto ptr = m_virtual_machine.binary_function(listing[1]);
            m_binary_functions[ptr].push_back(truncated);
        } break;

        case GIVEN_SYMMETRIC_FUNCTION: {
            auto ptr = m_virtual_machine.symmetric_function(listing[1]);
            m_symmetric_functions[ptr].push_back(truncated);
        } break;

        case FOR_BLOCK: {
            m_cleanup_large.push_back(truncated);
        } break;

        default: {
            m_cleanup_small.push_back(listing);
        } break;
    }
}

} // namespace vm
} // namespace pomagma
