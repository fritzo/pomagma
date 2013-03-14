#include "aggregator.hpp"

namespace pomagma
{

void aggregate (
        Structure & destin,
        Structure & src)
{
    POMAGMA_ASSERT(& destin != & src, "cannot merge structure into self");
    TODO("create partial equivalence relation between src, destin");
}

} // namespace pomagma
