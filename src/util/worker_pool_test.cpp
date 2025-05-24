#include <gtest/gtest.h>

#include <atomic>
#include <pomagma/util/util.hpp>
#include <pomagma/util/worker_pool.hpp>
#include <utility>

namespace pomagma {
namespace {

typedef std::pair<size_t, size_t> TestParam;
class WorkerPoolTest : public ::testing::TestWithParam<TestParam> {};

TEST_P(WorkerPoolTest, IsCorrect) {
    const size_t thread_count = GetParam().first;
    const size_t max_duration = GetParam().first;
    POMAGMA_INFO("Testing pool of " << thread_count << " threads "
                                    << "with tasks taking up to "
                                    << max_duration << "ms");
    ASSERT_LT(0UL, thread_count);

    std::atomic<uint_fast64_t> counter(0);
    {
        WorkerPool pool(thread_count);
        for (size_t duration = 0; duration <= max_duration; ++duration) {
            POMAGMA_DEBUG("scheduling sleep for " << duration << "ms");
            pool.schedule([duration, &counter] {
                POMAGMA_DEBUG("sleeping for " << duration << "ms");
                std::this_thread::sleep_for(
                    std::chrono::milliseconds(duration));
                size_t count = ++counter;
                POMAGMA_DEBUG("count = " << count);
            });
        }
    }
    ASSERT_EQ(counter, 1 + max_duration);
}

INSTANTIATE_TEST_CASE_P(AllParams, WorkerPoolTest,
                        ::testing::Values(TestParam(1, 20), TestParam(10, 100),
                                          TestParam(10, 20)));

}  // namespace
}  // namespace pomagma
