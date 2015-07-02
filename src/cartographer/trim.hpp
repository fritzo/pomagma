
#pragma once

#include <pomagma/atlas/world/util.hpp>
#include <pomagma/atlas/world/structure.hpp>

namespace pomagma
{

void trim (
        Structure & src,
        Structure & destin,
        const char * theory_file,
        const char * language_file,
        bool temperature = 1);

} // namespace pomagma
