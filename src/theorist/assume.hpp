#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure.hpp>
#include <map>

namespace pomagma {

std::map<std::string, size_t> assume (
        Structure & structure,
        const char * theory_file);

} // namespace pomagma
