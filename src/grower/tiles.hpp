#pragma once

#include <pomagma/grower/util.hpp>
#include <atomic>

namespace pomagma
{

//----------------------------------------------------------------------------
// tiled tiles of atomic Ob

static_assert(sizeof(Ob) == sizeof(std::atomic<Ob>),
        "std::atomic<Ob> is larger than Ob");

const size_t LOG2_ITEMS_PER_TILE = 3;
const size_t ITEMS_PER_TILE = 1 << LOG2_ITEMS_PER_TILE;
const size_t TILE_POS_MASK = ITEMS_PER_TILE - 1;
typedef std::atomic<Ob> Tile[ITEMS_PER_TILE * ITEMS_PER_TILE];

inline std::atomic<Ob> & _tile2value (std::atomic<Ob> * tile, Ob i, Ob j)
{
    POMAGMA_ASSERT6(i < ITEMS_PER_TILE, "out of range " << i);
    POMAGMA_ASSERT6(j < ITEMS_PER_TILE, "out of range " << j);
    return tile[(j << LOG2_ITEMS_PER_TILE) | i];
}

inline Ob _tile2value (const std::atomic<Ob> * tile, Ob i, Ob j)
{
    POMAGMA_ASSERT6(i < ITEMS_PER_TILE, "out of range " << i);
    POMAGMA_ASSERT6(j < ITEMS_PER_TILE, "out of range " << j);
    return tile[(j << LOG2_ITEMS_PER_TILE) | i];
}

} // namespace pomagma
