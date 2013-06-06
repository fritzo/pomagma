#pragma once

#include <string>
#include <unordered_map>

namespace pomagma
{

std::unordered_map<std::string, float> load_language (const char * filename);

} // namespace pomagma
