#pragma once

#include <atomic>
#include <pomagma/util/util.hpp>

namespace pomagma {

// Ob is a 1-based index type with 0 = none
#ifndef POMAGMA_OB_BITWIDTH
#define POMAGMA_OB_BITWIDTH 16
#endif  // POMAGMA_OB_BITWIDTH
#if POMAGMA_OB_BITWIDTH == 16
typedef uint16_t Ob;
#elif POMAGMA_OB_BITWIDTH == 32
typedef uint32_t Ob;
#endif  // POMAGMA_OB_BITWIDTH

static_assert(sizeof(Ob) == sizeof(std::atomic<Ob>),
              "std::atomic<Ob> is larger than Ob");

static constexpr size_t DEFAULT_ITEM_DIM = BITS_PER_CACHE_LINE - 1;
static constexpr size_t MAX_ITEM_DIM = (1UL << (8UL * sizeof(Ob))) - 1UL;

// Hash constants with good distribution
static constexpr uint64_t HASH_PRIME1 = 11400714785074694791ULL;
static constexpr uint64_t HASH_PRIME2 = 14029467366897019727ULL;
static constexpr uint64_t FNV_OFFSET = 14695981039346656037ULL;
static constexpr uint64_t FNV_PRIME = 1099511628211ULL;

struct FastObHash {
    static size_t hash(size_t ob1) { return ob1 * FNV_PRIME + FNV_OFFSET; }

    static size_t hash(size_t ob1, size_t ob2) {
        uint64_t h = FNV_OFFSET;
        h = (h ^ ob1) * FNV_PRIME;
        h = (h ^ ob2) * FNV_PRIME;
        return h;
    }

    static size_t hash(size_t ob1, size_t ob2, size_t ob3) {
        uint64_t h = FNV_OFFSET;
        h = (h ^ ob1) * FNV_PRIME;
        h = (h ^ ob2) * FNV_PRIME;
        h = (h ^ ob3) * FNV_PRIME;
        return h;
    }

    static size_t hash(size_t ob1, size_t ob2, size_t ob3, size_t ob4) {
        uint64_t h = FNV_OFFSET;
        h = (h ^ ob1) * FNV_PRIME;
        h = (h ^ ob2) * FNV_PRIME;
        h = (h ^ ob3) * FNV_PRIME;
        h = (h ^ ob4) * FNV_PRIME;
        return h;
    }
};

struct ObPairHash {
    size_t operator()(const std::pair<Ob, Ob>& pair) const {
        static_assert(sizeof(size_t) == 8, "invalid sizeof(size_t)");
        uint64_t x = pair.first;
        uint64_t y = pair.second;
        uint64_t h = x * HASH_PRIME1;
        h ^= h >> 33;
        h += y * HASH_PRIME2;
        h ^= h >> 29;
        h *= HASH_PRIME1;
        h ^= h >> 32;
        return h;
    }
};

}  // namespace pomagma