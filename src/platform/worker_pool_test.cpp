#include <pomagma/platform/util.hpp>
#include <pomagma/platform/worker_pool.hpp>

using namespace pomagma;

struct Task
{
    std::chrono::milliseconds duration;
    void operator() ()
    {
        POMAGMA_DEBUG("sleeping for " << duration.count() << "ms");
        std::this_thread::sleep_for(duration);
    }
};

void test_threadpool (size_t thread_count, size_t max_duration)
{
    POMAGMA_INFO("Testing pool of " << thread_count << " threads");
    POMAGMA_ASSERT_LT(0, thread_count);
    WorkerPool<Task> pool(thread_count);
    for (size_t duration = 0; duration <= max_duration; ++duration) {
        POMAGMA_DEBUG("scheduling sleep for " << duration << "ms");
        Task task = {std::chrono::milliseconds(duration)};
        pool.schedule(task);
    }

    while (not pool.empty()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
}

int main ()
{
    test_threadpool(1, 20);
    test_threadpool(10, 100);

    return 0;
}
