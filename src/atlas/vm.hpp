#pragma once

// Assumes the following are included:
// pomagma/?structure/util.hpp
// pomagma/?structure/structure_impl.hpp

#include <map>
#include <unordered_map>
#include <pomagma/util/aligned_alloc.hpp>
#include <pomagma/atlas/program_fwd.hpp>
#include <pomagma/util/profiler.hpp>

namespace pomagma {
namespace vm {

typedef Context_<Ob, DenseSet::RawData> Context;

//----------------------------------------------------------------------------
// VirtualMachine

class VirtualMachine
{
public:

    enum {
        block_size = 64 // granularity of FOR_BLOCK/IF_BLOCK parallelism
        for_block_op_code = 47
    };

    VirtualMachine () : m_carrier(nullptr)
    {
        POMAGMA_ASSERT(is_aligned(this, 64), "VirtualMachine is misaligned");
    }

    void load (Signature & signature);

    void execute (Program program) const
    {
        POMAGMA_ASSERT1(not is_parallel(program), "program is parallel");
        Context * context = new_context();
        ProgramProfiler::Block profiler(context->profiler, program);
        _execute(program, context);
    }

    void execute (Program program, Ob arg) const
    {
        POMAGMA_ASSERT1(not is_parallel(program), "program is parallel");
        Context * context = new_context();
        context->obs[0] = arg;
        ProgramProfiler::Block profiler(context->profiler, program);
        _execute(program, context);
    }

    void execute (Program program, Ob arg1, Ob arg2) const
    {
        POMAGMA_ASSERT1(not is_parallel(program), "program is parallel");
        Context * context = new_context();
        context->obs[0] = arg1;
        context->obs[1] = arg2;
        ProgramProfiler::Block profiler(context->profiler, program);
        _execute(program, context);
    }

    void execute (Program program, Ob arg1, Ob arg2, Ob arg3) const
    {
        POMAGMA_ASSERT1(not is_parallel(program), "program is parallel");
        Context * context = new_context();
        context->obs[0] = arg1;
        context->obs[1] = arg2;
        context->obs[2] = arg3;
        ProgramProfiler::Block profiler(context->profiler, program);
        _execute(program, context);
    }

    void execute_block (Program program, size_t block) const
    {
        // FIXME this should ERROR if run on world (cartographer, analyst)
        POMAGMA_ASSERT1(is_parallel(program), "program is not parallel");
        Context * context = new_context();
        context->block = block;
        ProgramProfiler::Block profiler(context->profiler, program);
        _execute(program, context);
    }

    const UnaryRelation * unary_relation (uint8_t index) const;
    const BinaryRelation * binary_relation (uint8_t index) const;
    const NullaryFunction * nullary_function (uint8_t index) const;
    const InjectiveFunction * injective_function (uint8_t index) const;
    const BinaryFunction * binary_function (uint8_t index) const;
    const SymmetricFunction * symmetric_function (uint8_t index) const;

private:

    static bool is_parallel (Program program)
    {
        return program[0] == for_block_op_code;
    }

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

    static const DenseSet::RawData * & pop_set (
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
    void add_listing (const ProgramParser & parser, const Listing & listing);
    void log_stats () const;
    const std::map<const void *, size_t> & get_linenos () { return m_linenos; }

    void execute (Ob ob) const
    {
        for (const auto & program : m_exists) {
            m_virtual_machine.execute(program, ob);
        }
    }

    void execute (const UnaryRelation * rel, Ob key) const
    {
        auto i = m_structures.find(rel);
        if (i != m_structures.end()) {
            for (const auto & program : i->second) {
                m_virtual_machine.execute(program, key);
            }
        }
    }

    void execute (const BinaryRelation * rel, Ob lhs, Ob rhs) const
    {
        auto i = m_structures.find(rel);
        if (i != m_structures.end()) {
            for (Program program : i->second) {
                m_virtual_machine.execute(program, lhs, rhs);
            }
        }
    }

    void execute (const NullaryFunction * fun) const
    {
        auto i = m_structures.find(fun);
        if (i != m_structures.end()) {
            for (Program program : i->second) {
                m_virtual_machine.execute(program);
            }
        }
    }

    void execute (const InjectiveFunction * fun, Ob key) const
    {
        auto i = m_structures.find(fun);
        if (i != m_structures.end()) {
            for (Program program : i->second) {
                m_virtual_machine.execute(program, key);
            }
        }
    }

    void execute (const BinaryFunction * fun, Ob lhs, Ob rhs) const
    {
        auto i = m_structures.find(fun);
        if (i != m_structures.end()) {
            for (Program program : i->second) {
                m_virtual_machine.execute(program, lhs, rhs);
            }
        }
    }

    void execute (const SymmetricFunction * fun, Ob lhs, Ob rhs) const
    {
        auto i = m_structures.find(fun);
        if (i != m_structures.end()) {
            for (Program program : i->second) {
                m_virtual_machine.execute(program, lhs, rhs);
            }
        }
    }

    void execute_cleanup (unsigned long index) const
    {
        POMAGMA_ASSERT_LT(0, m_block_count);
        const unsigned long small_count = m_cleanup_small.size();
        if (index < small_count) {
            Program program = m_cleanup_small[index];

            POMAGMA_DEBUG("executing cleanup task " << index);
            m_virtual_machine.execute(program);
        } else {
            index -= small_count;
            unsigned long block = index % m_block_count;
            index = index / m_block_count;
            Program program = m_cleanup_large[index];

            POMAGMA_DEBUG(
                "executing cleanup task " << (small_count + index) <<
                ", block " << block << " / " << m_block_count);
            m_virtual_machine.execute_block(program, block);
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

    typedef std::vector<Program> Programs;

    void add_program_to (
            Programs & programs,
            Program program,
            size_t size,
            size_t lineno);

    size_t count_bytes (const Programs & programs) const;

    VirtualMachine m_virtual_machine;
    Programs m_exists;
    std::unordered_map<const void *, Programs> m_structures;
    Programs m_cleanup_small;
    Programs m_cleanup_large;
    size_t m_block_count;
    std::map<std::string, const void *> m_names;
    std::map<const void *, size_t> m_sizes;
    std::map<const void *, size_t> m_linenos;
};

} // namespace vm
} // namespacepomagma
