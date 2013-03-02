#pragma once
// WARNING this should only be linked to once

#include "util.hpp"
#include "carrier.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include "binary_relation.hpp"
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
Sampler sampler(structure.signature());
void load_structure (const std::string & filename) { structure.load(filename); }
void dump_structure (const std::string & filename) { structure.dump(filename); }

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

inline void assume_equal (const char * lhs, const char * rhs)
{
    schedule(AssumeTask(AssumeTask::EQUAL, lhs, rhs));
}

inline void assume_less (const char * lhs, const char * rhs)
{
    schedule(AssumeTask(AssumeTask::LESS, lhs, rhs));
}

inline void assume_nless (const char * lhs, const char * rhs)
{
    schedule(AssumeTask(AssumeTask::NLESS, lhs, rhs));
}

inline Ob parse_ob (const char * source)
{
    Ob ob = sampler.try_insert(source);
    POMAGMA_ASSERT(ob, "failed to insert " << source);
    return ob;
}

void execute (const AssumeTask & task)
{
    Ob lhs = parse_ob(task.lhs);
    Ob rhs = parse_ob(task.rhs);

    switch (task.type) {
        case AssumeTask::EQUAL: {
            POMAGMA_INFO("assume EQUAL\n\t" << task.lhs << "\n\t" << task.rhs);
            ensure_equal(lhs, rhs);
        } break;

        case AssumeTask::LESS: {
            POMAGMA_INFO("assume LESS\n\t" << task.lhs << "\n\t" << task.rhs);
            ensure_less(lhs, rhs);
        } break;

        case AssumeTask::NLESS: {
            POMAGMA_INFO("assume LESS\n\t" << task.lhs << "\n\t" << task.rhs);
            ensure_nless(lhs, rhs);
        } break;
    }
}

//----------------------------------------------------------------------------
// sample tasks

bool sample_tasks_try_pop (SampleTask &)
{
    return carrier.item_count() < carrier.item_dim();
}

void execute (const SampleTask &, rng_t & rng)
{
    sampler.try_insert_random(rng);
}

} // namespace pomagma
