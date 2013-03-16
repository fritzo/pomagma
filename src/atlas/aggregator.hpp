#pragma once

#include "structure.hpp"

namespace pomagma
{

void aggregate (
        Structure & destin, // may grow or shrink
        Structure & src);   // may only shrink

} // namespace pomagma
