
#pragma once

#include "structure.hpp"

namespace pomagma
{

void trim (
        Structure & src,
        Structure & destin,
        const char * laws_file,
        const char * language_file);

} // namespace pomagma
