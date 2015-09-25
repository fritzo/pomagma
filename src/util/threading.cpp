#include <pomagma/util/threading.hpp>
#include <thread>
#include <unistd.h>

namespace pomagma {

size_t get_cpu_count ()
{
#if defined(__GNUG__) && (GCC_VERSION < 40800)
    return sysconf(_SC_NPROCESSORS_ONLN);
#else // defined(__GNUG__) && (GCC_VERSION < 40800)
    return std::thread::hardware_concurrency();
#endif // defined(__GNUG__) && (GCC_VERSION < 40800)
}

} // namespace pomagma
