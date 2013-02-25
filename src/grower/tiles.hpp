#pragma once

#include <pomagma/util/util.hpp>
#include <atomic>

namespace pomagma
{

//----------------------------------------------------------------------------
// tiled blocks of atomic Ob

static_assert(sizeof(Ob) == sizeof(std::atomic<Ob>),
        "std::atomic<Ob> is larger than Ob");

const size_t LOG2_ITEMS_PER_BLOCK = 3;
const size_t ITEMS_PER_BLOCK = 1 << LOG2_ITEMS_PER_BLOCK;
const size_t BLOCK_POS_MASK = ITEMS_PER_BLOCK - 1;
typedef std::atomic<Ob> Block[ITEMS_PER_BLOCK * ITEMS_PER_BLOCK];

inline std::atomic<Ob> & _block2value (std::atomic<Ob> * block, Ob i, Ob j)
{
    POMAGMA_ASSERT6(i < ITEMS_PER_BLOCK, "out of range " << i);
    POMAGMA_ASSERT6(j < ITEMS_PER_BLOCK, "out of range " << j);
    return block[(j << LOG2_ITEMS_PER_BLOCK) | i];
}

inline Ob _block2value (const std::atomic<Ob> * block, Ob i, Ob j)
{
    POMAGMA_ASSERT6(i < ITEMS_PER_BLOCK, "out of range " << i);
    POMAGMA_ASSERT6(j < ITEMS_PER_BLOCK, "out of range " << j);
    return block[(j << LOG2_ITEMS_PER_BLOCK) | i];
}

} // namespace pomagma
