#pragma once

#include <pomagma/atlas/macro/util.hpp>
#include <pomagma/atlas/macro/structure.hpp>

namespace pomagma {

float hypothesize_entropy(
    Structure& structure,
    const std::unordered_map<std::string, float>& language,
    const std::pair<Ob, Ob>& equation, float reltol = 1e-2f);

}  // namespace pomagma
