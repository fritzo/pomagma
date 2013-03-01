#pragma once

#include <pomagma/util/util.hpp>

namespace pomagma
{

namespace sequential {}
using namespace sequential;

//----------------------------------------------------------------------------
// Obs

// Ob is a 1-based index type with 0 = none
typedef uint32_t Ob;
const size_t MAX_ITEM_DIM = (1UL << (8UL * sizeof(Ob))) - 1UL;

struct ObPairHash
{
    size_t operator() (const std::pair<Ob, Ob> & key) const
    {
        static_assert(sizeof(key) == sizeof(size_t), "hasher fails");
        return * reinterpret_cast<const size_t * >(& key);
    }
};

} // namespace pomagma
