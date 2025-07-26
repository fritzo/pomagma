#pragma once

#include <pomagma/util/util.hpp>

namespace pomagma {

// Ob is a 1-based index type with 0 = none
#if POMAGMA_OB_BITWIDTH == 16
typedef uint16_t Ob;
#elif POMAGMA_OB_BITWIDTH == 32
typedef uint32_t Ob;
#endif  // POMAGMA_OB_BITWIDTH

static_assert(sizeof(Ob) == sizeof(std::atomic<Ob>),
              "std::atomic<Ob> is larger than Ob");

static constexpr size_t DEFAULT_ITEM_DIM = BITS_PER_CACHE_LINE - 1;
static constexpr size_t MAX_ITEM_DIM = (1UL << (8UL * sizeof(Ob))) - 1UL;
static constexpr size_t HASH_MULTIPLIER = 11400714819323198485ULL;

struct FastObHash {
    static size_t hash(size_t ob1) { return ob1; }

    static size_t hash(size_t ob1, size_t ob2) { return (ob1 << 32) | ob2; }

    static size_t hash(size_t ob1, size_t ob2, size_t ob3) {
        size_t state = (ob1 << POMAGMA_OB_BITWIDTH) | ob2;
        state *= HASH_MULTIPLIER;
        state += ob3;
        return state;
    }

    static size_t hash(size_t ob1, size_t ob2, size_t ob3, size_t ob4) {
        size_t state = (ob1 << POMAGMA_OB_BITWIDTH) | ob2;
        state *= HASH_MULTIPLIER;
        state += (ob3 << POMAGMA_OB_BITWIDTH) | ob4;
        return state;
    }
};

struct ObPairHash {
    size_t operator()(const std::pair<Ob, Ob>& pair) const {
        static_assert(sizeof(size_t) == 8, "invalid sizeof(size_t)");
        size_t x = pair.first;
        size_t y = pair.second;
        return ((x << POMAGMA_OB_BITWIDTH) | y) * HASH_MULTIPLIER;
    }
};

struct TrivialObPairHash {
    size_t operator()(const std::pair<Ob, Ob>& pair) const {
        static_assert(sizeof(size_t) == 8, "invalid sizeof(size_t)");
        size_t x = pair.first;
        size_t y = pair.second;
        return (x << POMAGMA_OB_BITWIDTH) | y;
    }
};

}  // namespace pomagma