#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure.hpp>
#include <pomagma/util/sequential/dense_set.hpp>

namespace pomagma
{

void aggregate (
        Structure & destin,
        Structure & src,
        const DenseSet & src_defined,
        bool clear_src = true);

} // namespace pomagma
