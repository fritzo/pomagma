#pragma once

#include <pomagma/util/util.hpp>

#define POMAGMA_USE_SPARSE_HASH 0

#if POMAGMA_USE_SPARSE_HASH == 1
#  include <google/sparse_hash_map>
#elif POMAGMA_USE_SPARSE_HASH == 2
#  include <google/dense_hash_map>
#else // POMAGMA_USE_SPARSE_HASH == 0
#  include <unordered_map>
#endif // POMAGMA_USE_SPARSE_HASH

#define POMAGMA_HAS_INVERSE_INDEX (0)
#define POMAGMA_CAN_PARALLELIZE (0)

namespace pomagma
{

namespace sequential {}
using namespace sequential;

//----------------------------------------------------------------------------
// Obs

// Ob is a 1-based index type with 0 = none
typedef uint32_t Ob;
static const size_t MAX_ITEM_DIM = (1UL << (8UL * sizeof(Ob))) - 1UL;
static const size_t HASH_MULTIPLIER = 11400714819323198485ULL;

struct FastObHash
{
    static size_t hash (size_t ob1)
    {
        return ob1;
    }

    static size_t hash (size_t ob1, size_t ob2)
    {
        return (ob1 << 32) | ob2;
    }

    static size_t hash (size_t ob1, size_t ob2, size_t ob3)
    {
        size_t state = (ob1 << 32) | ob2;
        state *= HASH_MULTIPLIER;
        state += ob3;
        return state;
    }

    static size_t hash (size_t ob1, size_t ob2, size_t ob3, size_t ob4)
    {
        size_t state = (ob1 << 32) | ob2;
        state *= HASH_MULTIPLIER;
        state += (ob3 << 32) | ob4;
        return state;
    }
};

struct ObPairHash
{
    size_t operator() (const std::pair<Ob, Ob> & pair) const
    {
        static_assert(sizeof(size_t) == 8, "invalid sizeof(size_t)");
        size_t x = pair.first;
        size_t y = pair.second;
        return ((x << 32) | y) * HASH_MULTIPLIER;
    }
};

struct TrivialObPairHash
{
    size_t operator() (const std::pair<Ob, Ob> & pair) const
    {
        static_assert(sizeof(size_t) == 8, "invalid sizeof(size_t)");
        size_t x = pair.first;
        size_t y = pair.second;
        return (x << 32) | y;
    }
};

#if POMAGMA_USE_SPARSE_HASH == 1

struct ObPairMap : google::sparse_hash_map<std::pair<Ob, Ob>, Ob, ObPairHash>
{
    ObPairMap () { set_deleted_key({0, 0}); }
};

#elif POMAGMA_USE_SPARSE_HASH == 2

struct ObPairMap : google::dense_hash_map<std::pair<Ob, Ob>, Ob, ObPairHash>
{
    ObPairMap ()
    {
        set_empty_key({0, 0});
        set_deleted_key({0, 1});
    }
};

#else // POMAGMA_USE_SPARSE_HASH == 0

typedef std::unordered_map<std::pair<Ob, Ob>, Ob, TrivialObPairHash> ObPairMap;

#endif // POMAGMA_USE_SPARSE_HASH

} // namespace pomagma
