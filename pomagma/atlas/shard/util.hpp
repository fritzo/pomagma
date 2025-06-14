#pragma once

#include <pomagma/util/util.hpp>
#include <unordered_map>

#define POMAGMA_HAS_INVERSE_INDEX (1)

namespace pomagma {
namespace sequential {}
namespace shard {
using namespace ::pomagma::sequential;

typedef uint32_t topic_t;

//----------------------------------------------------------------------------
// Obs

// Ob is a 1-based index type with 0 = none
typedef uint32_t Ob;
static const size_t MAX_ITEM_DIM = (1UL << (8UL * sizeof(Ob))) - 1UL;
static const size_t HASH_MULTIPLIER = 11400714819323198485ULL;

struct TrivialObHash {
    size_t operator()(const Ob& ob) const { return ob; }
};

struct TrivialObPairHash {
    size_t operator()(const std::pair<Ob, Ob>& pair) const {
        static_assert(sizeof(size_t) == 8, "invalid sizeof(size_t)");
        size_t x = pair.first;
        size_t y = pair.second;
        return (x << 32) | y;
    }
};

typedef std::unordered_map<std::pair<Ob, Ob>, Ob, TrivialObPairHash> ObPairMap;

}  // namespace shard
}  // namespace pomagma
