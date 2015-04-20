#pragma once

#include <unordered_map>
#include <pomagma/platform/aligned_alloc.hpp>
#include "theory.hpp"

namespace pomagma
{
namespace vm
{

enum OpCode : uint8_t;

class Parser
{
public:

    Parser (Signature & signature);
    std::vector<std::vector<uint8_t>> parse (std::istream & infile) const;

private:

    std::unordered_map<std::string, OpCode> m_op_codes;
    std::unordered_map<std::string, uint8_t> m_unary_relations;
    std::unordered_map<std::string, uint8_t> m_binary_relations;
    std::unordered_map<std::string, uint8_t> m_nullary_functions;
    std::unordered_map<std::string, uint8_t> m_injective_functions;
    std::unordered_map<std::string, uint8_t> m_binary_functions;
    std::unordered_map<std::string, uint8_t> m_symmetric_functions;

    class SymbolTable;
};

class VirtualMachine
{
public:

    VirtualMachine (Signature & signature);

    struct Context
    {
        Ob obs[256];
        const std::atomic<Word> * sets[256];
        size_t block;

        void clear ()
        {
            std::fill(std::begin(obs), std::end(obs), 0);
            std::fill(std::begin(sets), std::end(sets), nullptr);
            block = 0;
        }
    };

    typedef const uint8_t * Program;

    void execute (Program program, Context * context)
    {
        if (POMAGMA_DEBUG_LEVEL) {
            context->clear();
        }
        _execute(program, context);
    }

private:

    void _execute (Program program, Context * context);

    UnaryRelation * m_unary_relations[256];
    BinaryRelation * m_binary_relations[256];
    NullaryFunction * m_nullary_functions[256];
    InjectiveFunction * m_injective_functions[256];
    BinaryFunction * m_binary_functions[256];
    SymmetricFunction * m_symmetric_functions[256];
    Carrier & m_carrier;

    static uint8_t pop_arg (Program & program) { return *program++; }

    static OpCode pop_op_code (Program & program)
    {
        return static_cast<OpCode>(pop_arg(program));
    }

    static Ob & pop_ob (Program & program, Context * context)
    {
        return context->obs[pop_arg(program)];
    }

    static const std::atomic<Word> * & pop_set (
            Program & program,
            Context * context)
    {
        return context->sets[pop_arg(program)];
    }

    UnaryRelation & pop_unary_relation (Program & program)
    {
        return * m_unary_relations[pop_arg(program)];
    }

    BinaryRelation & pop_binary_relation (Program & program)
    {
        return * m_binary_relations[pop_arg(program)];
    }

    NullaryFunction & pop_nullary_function (Program & program)
    {
        return * m_nullary_functions[pop_arg(program)];
    }

    InjectiveFunction & pop_injective_function (Program & program)
    {
        return * m_injective_functions[pop_arg(program)];
    }

    BinaryFunction & pop_binary_function (Program & program)
    {
        return * m_binary_functions[pop_arg(program)];
    }

    SymmetricFunction & pop_symmetric_function (Program & program)
    {
        return * m_symmetric_functions[pop_arg(program)];
    }

    Carrier & carrier () { return m_carrier; }
    const DenseSet & support () { return m_carrier.support(); }
    size_t item_dim () { return support().item_dim(); }
    size_t word_dim () { return support().word_dim(); }

} __attribute__ ((aligned (64)));

} // namespace vm
} // namespacepomagma
