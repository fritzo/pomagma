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

void schedule_merge (Ob dep) { schedule(MergeTask(dep)); }
void schedule_less (Ob lhs, Ob rhs) { schedule(PositiveOrderTask(lhs, rhs)); }
void schedule_nless (Ob lhs, Ob rhs) { schedule(NegativeOrderTask(lhs, rhs)); }

Carrier carrier(DEFAULT_ITEM_DIM, schedule_merge);
inline size_t item_dim () { return carrier.support().item_dim(); }

BinaryRelation LESS(carrier, schedule_less);
BinaryRelation NLESS(carrier, schedule_nless);

//----------------------------------------------------------------------------
// ensurers

inline void ensure_equal (Ob lhs, Ob rhs) { carrier.ensure_equal(lhs, rhs); }

// TODO most uses of this can be vectorized
// TODO use .contains_Lx/.contains_Rx based on iterator direction
inline void ensure_less (Ob lhs, Ob rhs) { LESS.insert(lhs, rhs); }
inline void ensure_nless (Ob lhs, Ob rhs) { NLESS.insert(lhs, rhs); }

} // namespace pomagma

#endif // POMAGMA_THEORY_HPP
