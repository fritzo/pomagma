#pragma once

#include "util.hpp"
#include "structure.hpp"
#include <string>
#include <vector>
#include <unordered_map>

namespace pomagma
{

void conjecture_shallow (
        Structure & structure,
        const char * language_file,
        const char * conjectures_file,
        size_t max_count = 1000);

void conjecture_deep (
        Structure & structure,
        const char * language_file,
        const char * conjectures_file,
        size_t max_count = 100);

} // namespace pomagma
