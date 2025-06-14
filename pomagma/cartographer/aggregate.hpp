#pragma once

#include <pomagma/atlas/macro/structure.hpp>
#include <pomagma/atlas/macro/util.hpp>
#include <pomagma/util/sequential/dense_set.hpp>

namespace pomagma {

void aggregate(Structure& destin, Structure& src, const DenseSet& src_defined,
               bool clear_src = true);

}  // namespace pomagma
