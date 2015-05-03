#pragma once

#include <map>
#include <unordered_map>
#include <pomagma/platform/aligned_alloc.hpp>
#include <pomagma/microstructure/util.hpp>
#include <pomagma/microstructure/structure_impl.hpp>
#include "profiler.hpp"

namespace pomagma
{
namespace vm
{

enum { block_size = 64 };

typedef std::vector<uint8_t> Listing;

enum OpCode : uint8_t;
enum OpArgType : uint8_t;

//----------------------------------------------------------------------------
// Parser

class Parser
{
public:

    Parser (Signature & signature);
    std::vector<std::pair<Listing, size_t>> parse (std::istream & infile) const;
    std::vector<std::pair<Listing, size_t>> parse_file (
            const std::string & filename) const;

private:

    std::map<std::string, OpCode> m_op_codes;
    std::map<std::pair<OpArgType, std::string>, uint8_t> m_constants;

    class SymbolTable;
    class SymbolTableStack;
};

//----------------------------------------------------------------------------
// VirtualMachine

class VirtualMachine
{
public:

    VirtualMachine () : m_carrier(nullptr)
    {
        POMAGMA_ASSERT(is_aligned(this, 64), "VirtualMachine is misaligned");
    }

    void load (Signature & signature);

    void execute (const Listing & listing) const
    {
        Context * context = new_context();
        ProgramProfiler::Block profiler(context->profiler, listing.data());
        _execute(listing.data(), context);
    }

    void execute (const Listing & listing, Ob arg) const
    {
        Context * context = new_context();
        context->obs[0] = arg;
        ProgramProfiler::Block profiler(context->profiler, listing.data());
        _execute(listing.data(), context);
    }

    void execute (const Listing & listing, Ob arg1, Ob arg2) const
    {
        Context * context = new_context();
        context->obs[0] = arg1;
        context->obs[1] = arg2;
        ProgramProfiler::Block profiler(context->profiler, listing.data());
        _execute(listing.data(), context);
    }

    void execute (const Listing & listing, Ob arg1, Ob arg2, Ob arg3) const
    {
        Context * context = new_context();
        context->obs[0] = arg1;
        context->obs[1] = arg2;
        context->obs[2] = arg3;
        ProgramProfiler::Block profiler(context->profiler, listing.data());
        _execute(listing.data(), context);
    }

    void execute_block (const Listing & listing, size_t block) const
    {
        Context * context = new_context();
        context->block = block;
        ProgramProfiler::Block profiler(context->profiler, listing.data());
        _execute(listing.data(), context);
    }

    const UnaryRelation * unary_relation (uint8_t index) const;
    const BinaryRelation * binary_relation (uint8_t index) const;
    const NullaryFunction * nullary_function (uint8_t index) const;
    const InjectiveFunction * injective_function (uint8_t index) const;
    const BinaryFunction * binary_function (uint8_t index) const;
    const SymmetricFunction * symmetric_function (uint8_t index) const;

private:

    typedef const uint8_t * Program;

    struct Context
    {
        Ob obs[256];
        const std::atomic<Word> * sets[256];
        size_t block;
        size_t trace;
        ProgramProfiler profiler;

        void clear ()
        {
            std::fill(std::begin(obs), std::end(obs), 0);
            std::fill(std::begin(sets), std::end(sets), nullptr);
            block = 0;
            trace = 0;
        }
    } __attribute__((aligned(64)));

    static Context * new_context ()
    {
        // never freed
        static thread_local Context * context = nullptr;
        if (unlikely(context == nullptr)) {
            context = new Context;
            context->clear();
        }
        if (POMAGMA_DEBUG_LEVEL) {
            context->clear();
        }
        return context;
    }

    void _execute (Program program, Context * context) const;

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

    UnaryRelation & pop_unary_relation (Program & program) const
    {
        return * m_unary_relations[pop_arg(program)];
    }

    BinaryRelation & pop_binary_relation (Program & program) const
    {
        return * m_binary_relations[pop_arg(program)];
    }

    NullaryFunction & pop_nullary_function (Program & program) const
    {
        return * m_nullary_functions[pop_arg(program)];
    }

    InjectiveFunction & pop_injective_function (Program & program) const
    {
        return * m_injective_functions[pop_arg(program)];
    }

    BinaryFunction & pop_binary_function (Program & program) const
    {
        return * m_binary_functions[pop_arg(program)];
    }

    SymmetricFunction & pop_symmetric_function (Program & program) const
    {
        return * m_symmetric_functions[pop_arg(program)];
    }

    Carrier & carrier () const { return * m_carrier; }
    const DenseSet & support () const { return m_carrier->support(); }
    size_t item_dim () const { return support().item_dim(); }
    size_t word_dim () const { return support().word_dim(); }

    UnaryRelation * m_unary_relations[256];
    BinaryRelation * m_binary_relations[256];
    NullaryFunction * m_nullary_functions[256];
    InjectiveFunction * m_injective_functions[256];
    BinaryFunction * m_binary_functions[256];
    SymmetricFunction * m_symmetric_functions[256];
    Carrier * m_carrier;

} __attribute__ ((aligned (64)));

//----------------------------------------------------------------------------
// Agenda

class Agenda
{
public:

    Agenda () : m_block_count(0) {}

    void load (Signature & signature);
    void add_listing (const Listing & listing, size_t lineno);
    void log_stats () const;
    void optimize_listings ();
    const std::map<const void *, size_t> & get_linenos () { return m_linenos; }

    void execute (Ob ob) const
    {
        for (const auto & listing : m_exists) {
            m_virtual_machine.execute(listing, ob);
        }
    }

    void execute (const UnaryRelation * rel, Ob key) const
    {
        auto i = m_structures.find(rel);
        if (i != m_structures.end()) {
            for (const auto & listing : i->second) {
                m_virtual_machine.execute(listing, key);
            }
        }
    }

    void execute (const BinaryRelation * rel, Ob lhs, Ob rhs) const
    {
        auto i = m_structures.find(rel);
        if (i != m_structures.end()) {
            for (const Listing & listing : i->second) {
                m_virtual_machine.execute(listing, lhs, rhs);
            }
        }
    }

    void execute (const NullaryFunction * fun) const
    {
        auto i = m_structures.find(fun);
        if (i != m_structures.end()) {
            for (const Listing & listing : i->second) {
                m_virtual_machine.execute(listing);
            }
        }
    }

    void execute (const InjectiveFunction * fun, Ob key) const
    {
        auto i = m_structures.find(fun);
        if (i != m_structures.end()) {
            for (const Listing & listing : i->second) {
                m_virtual_machine.execute(listing, key);
            }
        }
    }

    void execute (const BinaryFunction * fun, Ob lhs, Ob rhs) const
    {
        auto i = m_structures.find(fun);
        if (i != m_structures.end()) {
            for (const Listing & listing : i->second) {
                m_virtual_machine.execute(listing, lhs, rhs);
            }
        }
    }

    void execute (const SymmetricFunction * fun, Ob lhs, Ob rhs) const
    {
        auto i = m_structures.find(fun);
        if (i != m_structures.end()) {
            for (const Listing & listing : i->second) {
                m_virtual_machine.execute(listing, lhs, rhs);
            }
        }
    }

    void execute_cleanup (unsigned long index) const
    {
        POMAGMA_ASSERT_LT(0, m_block_count);
        const unsigned long small_count = m_cleanup_small.size();
        if (index < small_count) {
            const Listing & listing = m_cleanup_small[index];

            POMAGMA_DEBUG("executing cleanup task " << index);
            m_virtual_machine.execute(listing);
        } else {
            index -= small_count;
            unsigned long block = index % m_block_count;
            index = index / m_block_count;
            const Listing & listing = m_cleanup_large[index];

            POMAGMA_DEBUG(
                "executing cleanup task " << (small_count + index) <<
                ", block " << block << " / " << m_block_count);
            m_virtual_machine.execute_block(listing, block);
        }
    }

    unsigned long cleanup_task_count () const
    {
        return m_cleanup_small.size() + m_cleanup_large.size() * m_block_count;
    }

    unsigned long cleanup_type_count () const
    {
        return m_cleanup_small.size() + m_cleanup_large.size();
    }

private:

    typedef std::vector<Listing> Listings;

    void add_listing_to (
            Listings & listings,
            const Listing & listing,
            size_t lineno);
    void sort_listings (Listings & listings);

    VirtualMachine m_virtual_machine;
    Listings m_exists;
    std::unordered_map<const void *, Listings> m_structures;
    Listings m_cleanup_small;
    Listings m_cleanup_large;
    size_t m_block_count;
    std::map<std::string, const void *> m_names;
    std::map<const void *, size_t> m_linenos;
};

} // namespace vm
} // namespacepomagma
