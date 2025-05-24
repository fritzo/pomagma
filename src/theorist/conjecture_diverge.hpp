#pragma once

#include <pomagma/atlas/macro/structure.hpp>
#include <pomagma/atlas/macro/util.hpp>
#include <string>
#include <unordered_map>
#include <vector>

namespace pomagma {

size_t conjecture_diverge(Structure& structure, const char* language_file,
                          const char* conjectures_file);

size_t conjecture_diverge(Structure& structure, const std::vector<float>& probs,
                          const std::vector<std::string>& routes,
                          const char* conjectures_file);

}  // namespace pomagma
