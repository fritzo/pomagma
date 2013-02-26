#pragma once

#include <pomagma/util/util.hpp>

namespace pomagma
{

//----------------------------------------------------------------------------
// Obs

// Ob is a 1-based index type with 0 = none
typedef uint32_t Ob;
const size_t MAX_ITEM_DIM = (1UL << (8UL * sizeof(Ob))) - 1UL;

} // namespace pomagma
