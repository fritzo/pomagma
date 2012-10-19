#pragma once

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

// TODO set item dim at run time
Carrier carrier(DEFAULT_ITEM_DIM, schedule_exists, schedule_merge);
inline size_t item_dim () { return carrier.item_dim(); }

Sampler sampler(carrier);

BinaryRelation LESS(carrier, schedule_less);
BinaryRelation NLESS(carrier, schedule_nless);

//----------------------------------------------------------------------------
// make expressions

inline Ob make ()
{
    Ob val = carrier.try_insert();
    POMAGMA_ASSERT(val, "make failed (out of space)");
    return val;
}

inline Ob make (NullaryFunction & fun)
{
    if (Ob val = fun.find()) {
        return val;
    } else {
        Ob val = make();
        fun.insert(val);
        return val;
    }
}

inline Ob make (InjectiveFunction & fun, Ob key)
{
    if (Ob val = fun.find(key)) {
        return val;
    } else {
        Ob val = make();
        fun.insert(key, val);
        return val;
    }
}

inline Ob make (BinaryFunction & fun, Ob lhs, Ob rhs)
{
    if (Ob val = fun.find(lhs, rhs)) {
        return val;
    } else {
        Ob val = make();
        fun.insert(lhs, rhs, val);
        return val;
    }
}

inline Ob make (SymmetricFunction & fun, Ob lhs, Ob rhs)
{
    if (Ob val = fun.find(lhs, rhs)) {
        return val;
    } else {
        Ob val = make();
        fun.insert(lhs, rhs, val);
        return val;
    }
}

//----------------------------------------------------------------------------
// sample tasks

bool sample_tasks_try_pop (SampleTask &)
{
    return carrier.item_count() != item_dim();
}

void execute (const SampleTask &)
{
    POMAGMA_ASSERT(carrier.item_count() != item_dim(),
            "tried to insert in full carrier");
    sampler.unsafe_insert_random();
}

} // namespace pomagma
