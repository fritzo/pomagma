#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure.hpp>

namespace pomagma
{

void aggregate (
        Structure & destin,
        Structure & src,
        bool clear_src = true);

} // namespace pomagma
