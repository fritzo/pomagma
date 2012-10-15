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
#include <future>
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

Carrier carrier(DEFAULT_ITEM_DIM, schedule_exists, schedule_merge);
inline size_t item_dim () { return carrier.item_dim(); }

Sampler sampler(carrier);

BinaryRelation LESS(carrier, schedule_less);
BinaryRelation NLESS(carrier, schedule_nless);

//----------------------------------------------------------------------------
// background task execution

void execute (const DiffuseTask &)
{
    static std::atomic<unsigned> ob(0);
    unsigned old_ob = ob.load();
    unsigned new_ob;
    do {
        new_ob = old_ob % item_dim() + 1;
        while (not carrier.contains(new_ob)) {
            new_ob = new_ob % item_dim() + 1;
        }
    } while (ob.compare_exchange_weak(old_ob, new_ob));

    sampler.update_one(new_ob); // TODO aggregate tasks
}

Ob execute (const SampleTask &)
{
    // TODO ASSERT(all obs are rep obs)
    if (carrier.item_count() == item_dim()) {
        return sampler.unsafe_remove_random();
    } else {
        sampler.unsafe_insert_random();
        return 0;
    }
}

} // namespace pomagma
