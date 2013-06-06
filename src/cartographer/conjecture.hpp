#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure.hpp>
#include <string>
#include <vector>
#include <unordered_map>

namespace pomagma
{

static const size_t DEFAULT_CONJECTURE_COUNT = 1000;

void conjecture_shallow (
        Structure & structure,
        const char * language_file,
        const char * conjectures_file,
        size_t max_count = DEFAULT_CONJECTURE_COUNT);

void conjecture_deep (
        Structure & structure,
        const char * language_file,
        const char * conjectures_file,
        size_t max_count = DEFAULT_CONJECTURE_COUNT);

} // namespace pomagma
