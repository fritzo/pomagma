#include <pomagma/util/util.hpp>
#include <pomagma/util/worker_pool.hpp>
#include <atomic>

using namespace pomagma;

void test_threadpool (
    size_t thread_count,
    size_t max_duration)
{
    POMAGMA_INFO("Testing pool of " << thread_count << " threads "
        << "with tasks taking up to " << max_duration << "ms");
    POMAGMA_ASSERT_LT(0, thread_count);

    std::atomic<uint_fast64_t> counter(0);
    {
        WorkerPool pool(thread_count);
        for (size_t duration = 0; duration <= max_duration; ++duration) {
            POMAGMA_DEBUG("scheduling sleep for " << duration << "ms");
            pool.schedule([duration, &counter]{
                POMAGMA_DEBUG("sleeping for " << duration << "ms");
                std::this_thread::sleep_for(
                    std::chrono::milliseconds(duration));
                size_t count = ++counter;
                POMAGMA_DEBUG("count = " << count);
            });
        }
    }
    POMAGMA_ASSERT_EQ(counter, 1 + max_duration);
}

int main ()
{
    test_threadpool(1, 20);
    test_threadpool(10, 100);
    test_threadpool(10, 20);

    return 0;
}
