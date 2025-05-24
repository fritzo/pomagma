#pragma once

#include <pomagma/atlas/macro/structure.hpp>
#include <pomagma/atlas/macro/util.hpp>

namespace pomagma {

static const int EXIT_CONSISTENT = EXIT_SUCCESS;
static const int EXIT_INCONSISTENT = EXIT_FAILURE;

void configure_scheduler_to_merge_if_consistent(Structure& structure);

}  // namespace pomagma
