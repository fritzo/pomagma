#pragma once

#include <pomagma/util/util.hpp>

namespace pomagma
{

//----------------------------------------------------------------------------
// data types

template<size_t bytes> struct uint_;
template<> struct uint_<1> { typedef uint8_t t; };
template<> struct uint_<2> { typedef uint16_t t; };
template<> struct uint_<4> { typedef uint32_t t; };
template<> struct uint_<8> { typedef uint64_t t; };

// Ob is a 1-based index type with 0 = none
typedef uint16_t Ob;
const size_t MAX_ITEM_DIM = (1UL << (8UL * sizeof(Ob))) - 1UL;

} // namespace pomagma
