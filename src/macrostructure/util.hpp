#pragma once

#include <pomagma/platform/util.hpp>

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

// TODO define a better ObHash and ObPairHash
// see references section of the google sparsehash performance page:
//   http://sparsehash.googlecode.com/svn/trunk/doc/performance.html

} // namespace pomagma
