
#pragma once

#include "structure.hpp"

namespace pomagma
{

void trim (
        Structure & src,
        Structure & destin,
        const char * laws_file,
        const char * vehicle_file);

} // namespace pomagma
