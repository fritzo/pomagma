#include "profiler.hpp"

namespace pomagma
{

std::vector<atomic_default<unsigned long>> CleanupProfiler::s_counts;
std::vector<atomic_default<unsigned long>> CleanupProfiler::s_elapsed;

} // namespace pomagma
