#pragma once

#include "util.hpp"
#include "structure.hpp"
#include <string>
#include <vector>
#include <unordered_map>

namespace pomagma
{

static const size_t DEFAULT_CONJECTURE_COUNT = 1000;

std::unordered_map<std::string, float> load_language (
        const char * language_file);

std::vector<float> measure_weights (
        Structure & structure,
        const std::unordered_map<std::string, float> & language,
        float reltol = 0.1);

std::vector<std::string> parse_all (
        Structure & structure,
        const std::unordered_map<std::string, float> & language);

void theorize (
        Structure & structure,
        const std::vector<float> & weights,
        const std::vector<std::string> & parses,
        const char * conjectures_file,
        size_t max_count = DEFAULT_CONJECTURE_COUNT);

} // namespace pomagma
