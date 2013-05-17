#pragma once

#include <pomagma/util/util.hpp>
#include <atomic>

namespace pomagma
{

namespace concurrent {}
using namespace concurrent;

//----------------------------------------------------------------------------
// Obs

// Ob is a 1-based index type with 0 = none
typedef uint16_t Ob;
static_assert(sizeof(Ob) == sizeof(std::atomic<Ob>),
        "std::atomic<Ob> is larger than Ob");

static const size_t MAX_ITEM_DIM = (1UL << (8UL * sizeof(Ob))) - 1UL;
static const size_t DEFAULT_ITEM_DIM = BITS_PER_CACHE_LINE - 1;

//----------------------------------------------------------------------------
// tiled blocks of atomic Ob

static const size_t LOG2_ITEMS_PER_TILE = 3;
static const size_t ITEMS_PER_TILE = 1 << LOG2_ITEMS_PER_TILE;
static const size_t TILE_POS_MASK = ITEMS_PER_TILE - 1;
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
