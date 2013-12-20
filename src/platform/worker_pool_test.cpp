#include <pomagma/platform/util.hpp>
#include <pomagma/platform/worker_pool.hpp>

using namespace pomagma;

struct Task
{
    std::chrono::milliseconds duration;
};

struct Processor
{
    void operator() (const Task & task)
    {
        POMAGMA_DEBUG("sleeping for " << task.duration.count() << "ms");
        std::this_thread::sleep_for(task.duration);
    }

};

void test_threadpool (
    size_t thread_count,
    size_t max_duration,
    size_t wait_count)
{
    POMAGMA_INFO("Testing pool of " << thread_count << " threads");
    POMAGMA_ASSERT_LT(0, thread_count);
    Processor processor;
    WorkerPool<Task, Processor> pool(processor, thread_count);
    for (size_t duration = 0; duration <= max_duration; ++duration) {
        POMAGMA_DEBUG("scheduling sleep for " << duration << "ms");
        pool.schedule(Task({std::chrono::milliseconds(duration)}));
    }
    for (size_t i = 0; i < wait_count; ++i) {
        pool.wait();
    }
}

int main ()
{
    test_threadpool(1, 20, 0);
    test_threadpool(10, 100, 0);
    test_threadpool(10, 20, 2);

    return 0;
}
