
#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure.hpp>

namespace pomagma
{

void trim (
        Structure & src,
        Structure & destin,
        const char * theory_file,
        const char * language_file,
        bool temperature = 1);

} // namespace pomagma
