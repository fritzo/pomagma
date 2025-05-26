#include <unistd.h>

#include <pomagma/util/threading.hpp>
#include <thread>

namespace pomagma {

size_t get_cpu_count() {
    if (getenv("CI")) {
        return 2;
    }
    return std::thread::hardware_concurrency();
}

}  // namespace pomagma
