#pragma once

#include <atomic>
#include <pomagma/atlas/obs.hpp>
#include <pomagma/util/util.hpp>

#define POMAGMA_HAS_INVERSE_INDEX (1)

namespace pomagma {

namespace concurrent {}
using namespace concurrent;

struct not_lazy {
    void lazy_gather() const {}
    void lazy_flush() const {}
};

//----------------------------------------------------------------------------
// tiled blocks of atomic Ob

// There are two 64B cache lines per square tile.
// The more common traversal pattern is fixed-lhs while varying-rhs.
static constexpr size_t LOG2_ITEMS_PER_TILE = 3;
static constexpr size_t ITEMS_PER_TILE = 1 << LOG2_ITEMS_PER_TILE;
static constexpr size_t TILE_POS_MASK = ITEMS_PER_TILE - 1;
typedef std::atomic<Ob> Tile[ITEMS_PER_TILE * ITEMS_PER_TILE];

inline std::atomic<Ob>& _tile2value(std::atomic<Ob>* tile, Ob i, Ob j) {
    POMAGMA_ASSERT6(i < ITEMS_PER_TILE, "out of range " << i);
    POMAGMA_ASSERT6(j < ITEMS_PER_TILE, "out of range " << j);
    return tile[(i << LOG2_ITEMS_PER_TILE) | j];
}

inline Ob _tile2value(const std::atomic<Ob>* tile, Ob i, Ob j) {
    POMAGMA_ASSERT6(i < ITEMS_PER_TILE, "out of range " << i);
    POMAGMA_ASSERT6(j < ITEMS_PER_TILE, "out of range " << j);
    return tile[(i << LOG2_ITEMS_PER_TILE) | j];
}

}  // namespace pomagma
