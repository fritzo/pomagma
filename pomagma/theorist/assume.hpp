#pragma once

#include <map>
#include <pomagma/atlas/macro/structure.hpp>
#include <pomagma/atlas/macro/util.hpp>

namespace pomagma {

std::map<std::string, size_t> assume(Structure& structure,
                                     const char* theory_file);

}  // namespace pomagma
