#pragma once

#include <pomagma/atlas/world/util.hpp>
#include <pomagma/atlas/world/structure.hpp>
#include <map>

namespace pomagma {

std::map<std::string, size_t> assume (
        Structure & structure,
        const char * theory_file);

} // namespace pomagma
