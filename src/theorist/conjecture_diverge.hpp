#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure.hpp>
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
