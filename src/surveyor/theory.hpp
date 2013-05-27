#pragma once
// WARNING this should only be linked to once

#include "util.hpp"
#include "carrier.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include "binary_relation.hpp"
#include "parser.hpp"
#include "sampler.hpp"
#include "structure.hpp"
#include "scheduler.hpp"
#include <pomagma/util/signature.hpp>
#include <atomic>
#include <thread>
#include <vector>

namespace pomagma
{

//----------------------------------------------------------------------------
// signature

Structure structure;
Signature & signature = structure.signature();
Parser parser(structure.signature());
Sampler sampler(structure.signature());

void load_structure (const std::string & filename) { structure.load(filename); }
void dump_structure (const std::string & filename) { structure.dump(filename); }
void load_language (const std::string & filename) { sampler.load(filename); }

void schedule_merge (Ob dep) { schedule(MergeTask(dep)); }
void schedule_exists (Ob ob) { schedule(ExistsTask(ob)); }
void schedule_less (Ob lhs, Ob rhs) { schedule(PositiveOrderTask(lhs, rhs)); }
void schedule_nless (Ob lhs, Ob rhs) { schedule(NegativeOrderTask(lhs, rhs)); }
void schedule_nullary_function (const NullaryFunction * fun)
{
    schedule(NullaryFunctionTask(*fun));
}
void schedule_injective_function (const InjectiveFunction * fun, Ob arg)
{
    schedule(InjectiveFunctionTask(*fun, arg));
}
void schedule_binary_function (const BinaryFunction * fun, Ob lhs, Ob rhs)
{
    schedule(BinaryFunctionTask(*fun, lhs, rhs));
}
void schedule_symmetric_function (const SymmetricFunction * fun, Ob lhs, Ob rhs)
{
    schedule(SymmetricFunctionTask(*fun, lhs, rhs));
}

Carrier carrier(
    getenv_default("POMAGMA_SIZE", DEFAULT_ITEM_DIM),
    schedule_exists,
    schedule_merge);

BinaryRelation LESS(carrier, schedule_less);
BinaryRelation NLESS(carrier, schedule_nless);

//----------------------------------------------------------------------------
// validation

void validate_all ()
{
    structure.validate();
    sampler.validate();
}

//----------------------------------------------------------------------------
// basic ensurers

inline void ensure_equal (Ob lhs, Ob rhs)
{
    carrier.ensure_equal(lhs, rhs);
}

inline void ensure_less (Ob lhs, Ob rhs)
{
    LESS.insert(lhs, rhs);
}

inline void ensure_nless (Ob lhs, Ob rhs)
{
    NLESS.insert(lhs, rhs);
}

//----------------------------------------------------------------------------
// expression parsing

void assume_core_facts (const char * theory_file)
{
    std::ifstream file(theory_file);
    POMAGMA_ASSERT(file, "failed to open " << theory_file);

    std::string expression;
    while (getline(file, expression)) {
        if (not expression.empty() and expression[0] != '#') {
            schedule(AssumeTask(expression));
        }
    }
}

void execute (const AssumeTask & task)
{
    POMAGMA_DEBUG("assume " << task.expression);
    std::istringstream expression(task.expression);

    std::string type;
    POMAGMA_ASSERT(getline(expression, type, ' '), "bad line: " << expression);
    Parser::Policy policy(carrier);
    Ob lhs = parser.parse_insert(expression, policy);
    Ob rhs = parser.parse_insert(expression, policy);
    POMAGMA_ASSERT(lhs and rhs, "parse_insert failed");

    if (type == "EQUAL") {
        ensure_equal(lhs, rhs);
	} else if (type == "LESS") {
        ensure_less(lhs, rhs);
	} else if (type == "NLESS") {
        ensure_nless(lhs, rhs);
	} else {
        POMAGMA_ERROR("bad relation type: " << type);
	}
}

//----------------------------------------------------------------------------
// sample tasks

void insert_nullary_functions ()
{
    const auto & functions = signature.nullary_functions();
    POMAGMA_INFO("Inserting " << functions.size() << " nullary functions");

    for (auto pair : functions) {
        NullaryFunction * fun = pair.second;
        if (not fun->find()) {
            Ob val = carrier.try_insert();
            POMAGMA_ASSERT(val, "no space to insert nullary functions");
            fun->insert(val);
        }
    }
}

bool sample_tasks_try_pop (SampleTask &)
{
    return carrier.item_count() < carrier.item_dim();
}

void execute (const SampleTask &, rng_t & rng)
{
    Sampler::Policy policy(carrier);
    sampler.try_insert_random(rng, policy);
}

//----------------------------------------------------------------------------
// task profiling

class CleanupProfiler
{
    static std::vector<atomic_default<unsigned long>> s_counts;
    static std::vector<atomic_default<unsigned long>> s_elapsed;

public:

    class Block
    {
        const unsigned long m_type;
        Timer m_timer;
    public:
        Block (unsigned long type) : m_type(type) {}
        ~Block ()
        {
            s_elapsed[m_type].fetch_add(
                m_timer.elapsed_us(),
                std::memory_order_acq_rel);
            s_counts[m_type].fetch_add(1, std::memory_order_acq_rel);
        }
    };

    CleanupProfiler (unsigned long task_count)
    {
        s_counts.resize(task_count);
        s_elapsed.resize(task_count);
    }

    ~CleanupProfiler ()
    {
        unsigned long task_count = s_counts.size();
        POMAGMA_INFO("Task Id\tCount\tElapsed sec");
        for (unsigned long i = 0; i < task_count; ++i) {
            POMAGMA_INFO(
                std::setw(4) << i <<
                std::setw(8) << s_counts[i].load() <<
                std::setw(16) << (s_elapsed[i].load() * 1e-6));
        }
    }
};

std::vector<atomic_default<unsigned long>> CleanupProfiler::s_counts;
std::vector<atomic_default<unsigned long>> CleanupProfiler::s_elapsed;

} // namespace pomagma