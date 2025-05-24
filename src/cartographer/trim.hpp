
#pragma once

#include <pomagma/atlas/macro/structure.hpp>
#include <pomagma/atlas/macro/util.hpp>

namespace pomagma {

void trim(Structure& src, Structure& destin, const char* theory_file,
          const char* language_file, bool temperature = 1);

}  // namespace pomagma
