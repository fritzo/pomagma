#ifndef POMAGMA_THEORY_HPP
#define POMAGMA_THEORY_HPP

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

void schedule_merge_task (Ob dep) { schedule(MergeTask(dep)); }

Carrier carrier(DEFAULT_ITEM_DIM, schedule_merge_task);
const DenseSet support(carrier.support(), yes_copy_construct);
inline size_t item_dim () { return support.item_dim(); }

BinaryRelation LESS(carrier);
BinaryRelation NLESS(carrier);

//----------------------------------------------------------------------------
// ensurers

inline void ensure_equal (Ob lhs, Ob rhs)
{
    carrier.ensure_equal(lhs, rhs);
}

// TODO most uses of this can be vectorized
// TODO use .contains_Lx/.contains_Rx based on iterator direction
inline void ensure_less (Ob lhs, Ob rhs)
{
    // TODO do this more atomically
    if (not LESS(lhs, rhs)) {
        LESS.insert(lhs, rhs);
        schedule(PositiveOrderTask(lhs, rhs));
    }
}

// TODO most uses of this can be vectorized
// TODO use .contains_Lx/.contains_Rx based on iterator direction
inline void ensure_nless (Ob lhs, Ob rhs)
{
    // TODO do this more atomically
    if (not NLESS(lhs, rhs)) {
        NLESS.insert(lhs, rhs);
        schedule(NegativeOrderTask(lhs, rhs));
    }
}

} // namespace pomagma

#endif // POMAGMA_THEORY_HPP
