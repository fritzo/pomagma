#pragma once

#include <pomagma/atlas/world/util.hpp>
#include <pomagma/atlas/world/structure.hpp>
#include <string>
#include <vector>
#include <unordered_map>

namespace pomagma
{

size_t conjecture_diverge (
        Structure & structure,
        const char * language_file,
        const char * conjectures_file);

size_t conjecture_diverge (
        Structure & structure,
        const std::vector<float> & probs,
        const std::vector<std::string> & routes,
        const char * conjectures_file);

} // namespace pomagma
