#include "scheduler.hpp"
#include <chrono>
#include <thread>

using namespace pomagma;

void test_simple (size_t max_threads = 20)
{
    for (size_t i = 1; i <= max_threads; ++i) {
        Scheduler::set_thread_count(i);
        schedule(ExistsTask(1));
        Scheduler::initialize();
        schedule(ExistsTask(1));
        Scheduler::grow();
    }
}

int main ()
{
    test_simple();

    return 0;
}
