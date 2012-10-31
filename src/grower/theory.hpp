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
#include "scheduler.hpp"
#include <atomic>
#include <thread>
#include <vector>

namespace pomagma
{

//----------------------------------------------------------------------------
// signature

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

Sampler sampler(carrier);

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

inline Ob parse (const char * source)
{
    Ob ob = sampler.try_insert(source);
    POMAGMA_ASSERT(ob, "failed to insert " << source);
    return ob;
}

inline void assume_equal (const char * lhs, const char * rhs)
{
    POMAGMA_INFO("assume EQUAL\n\t" << lhs << "\n\t" << rhs);
    ensure_equal(parse(lhs), parse(rhs));
}

inline void assume_less (const char * lhs, const char * rhs)
{
    POMAGMA_INFO("assume LESS\n\t" << lhs << "\n\t" << rhs);
    ensure_less(parse(lhs), parse(rhs));
}

inline void assume_nless (const char * lhs, const char * rhs)
{
    POMAGMA_INFO("assume LESS\n\t" << lhs << "\n\t" << rhs);
    ensure_nless(parse(lhs), parse(rhs));
}

//----------------------------------------------------------------------------
// sample tasks

bool sample_tasks_try_pop (SampleTask &)
{
    return carrier.item_count() < carrier.item_dim();
}

void execute (const SampleTask &)
{
    sampler.try_insert_random();
}

} // namespace pomagma
