#pragma once

#include <unordered_map>
#include <pomagma/platform/aligned_alloc.hpp>
#include "theory.hpp"

namespace pomagma
{
namespace vm
{

struct Operation;

enum OpCode : uint8_t;

struct Operation
{
    uint8_t data[8];

    OpCode op_code () const { return static_cast<OpCode>(data[0]); }
    const uint8_t * args () const { return data + 1; }
    uint8_t * args () { return data + 1; }
} __attribute__ ((aligned (8)));

class Parser
{
public:

    Parser (Signature & signature);
    std::vector<std::vector<Operation>> parse (std::istream & infile) const;

private:

    std::unordered_map<std::string, OpCode> m_op_codes;
    std::unordered_map<std::string, uint8_t> m_unary_relations;
    std::unordered_map<std::string, uint8_t> m_binary_relations;
    std::unordered_map<std::string, uint8_t> m_nullary_functions;
    std::unordered_map<std::string, uint8_t> m_injective_functions;
    std::unordered_map<std::string, uint8_t> m_binary_functions;
    std::unordered_map<std::string, uint8_t> m_symmetric_functions;

    mutable std::unordered_map<std::string, uint8_t> m_obs;

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

    void execute (const Operation * program, Context * context)
    {
        if (POMAGMA_DEBUG_LEVEL) {
            context->clear();
        }
        _execute(program, context);
    }

private:

    void _execute (const Operation * program, Context * context);

    UnaryRelation * m_unary_relations[256];
    BinaryRelation * m_binary_relations[256];
    NullaryFunction * m_nullary_functions[256];
    InjectiveFunction * m_injective_functions[256];
    BinaryFunction * m_binary_functions[256];
    SymmetricFunction * m_symmetric_functions[256];
    Carrier & m_carrier;

    static uint8_t pop_arg (const uint8_t * & args)
    {
        POMAGMA_ASSERT5(not is_aligned(args, 8), "pop_arg'd past end of args");
        return *args++;
    }

    static Ob & pop_ob (const uint8_t * & args, Context * context)
    {
        return context->obs[pop_arg(args)];
    }

    static const std::atomic<Word> * & pop_set (
            const uint8_t * & args,
            Context * context)
    {
        return context->sets[pop_arg(args)];
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
