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

    class SymbolTable
    {
        std::unordered_map<std::string, uint8_t> m_registers;

    public:

        void clear () { m_registers.clear(); }

        uint8_t operator() (const std::string & name)
        {
            auto i = m_registers.find(name);
            if (i != m_registers.end()) {
                return i->second;
            } else {
                POMAGMA_ASSERT(
                    m_registers.size() < 256,
                    "too many variables for registers; limit = 256");
                uint8_t index = m_registers.size();
                m_registers.insert(std::make_pair(name, index));
                return index;
            }
        }
    };

    mutable std::unordered_map<std::string, uint8_t> m_obs;
};

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
