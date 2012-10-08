#pragma once

#include "util.hpp"
#include "carrier.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include "binary_relation.hpp"
#include "scheduler.hpp"
#include <atomic>
#include <vector>

namespace pomagma
{

//----------------------------------------------------------------------------
// signature

void schedule_merge (Ob dep) { schedule(MergeTask(dep)); }
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

Carrier carrier(DEFAULT_ITEM_DIM, schedule_merge);
inline size_t item_dim () { return carrier.support().item_dim(); }

BinaryRelation LESS(carrier, schedule_less);
BinaryRelation NLESS(carrier, schedule_nless);

} // namespace pomagma
