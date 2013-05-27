#pragma once

#include "util.hpp"
#include "structure.hpp"
#include <string>
#include <vector>
#include <unordered_map>

namespace pomagma
{

static const size_t DEFAULT_CONJECTURE_COUNT = 1000;

void conjecture (
        Structure & structure,
        const char * language_file,
        const char * conjectures_file,
        size_t max_count = DEFAULT_CONJECTURE_COUNT);

} // namespace pomagma
