#include <gtest/gtest.h>
#include <pomagma/util/async_map.hpp>
#include <pomagma/util/util.hpp>
#include <pomagma/util/worker_pool.hpp>

namespace pomagma {
namespace {

typedef const std::pair<int, int>* Key;
typedef int Value;

typedef AsyncMap<Key, Value> Cache;

TEST(AsyncMapTest, IsCorrect) {
    const size_t thread_count = 10;
    const size_t eval_count = 100;
    const size_t max_wait = 100;

    WorkerPool pool(thread_count);
    Cache cache([&pool](Key key, Cache::Callback callback) {
        pool.schedule([key, callback] {
            Value* value = new Value(key->first + key->second);
            std::this_thread::sleep_for(std::chrono::milliseconds(*value));
            callback(value);
        });
    });

    std::random_device device;
    rng_t rng(device());
    std::uniform_int_distribution<> random_int(0, max_wait);

    std::atomic<uint_fast64_t> pending_count(eval_count);

    for (size_t i = 0; i < eval_count; ++i) {
        POMAGMA_INFO("starting task " << i);
        Key key = new std::pair<int, int>(random_int(rng), random_int(rng));
        auto delay = std::chrono::milliseconds(random_int(rng));
        new std::thread([delay, &cache, key, &pending_count, i] {
            std::this_thread::sleep_for(delay);
            cache.find_async(key, [&pending_count, i](const Value*) {
                --pending_count;
                POMAGMA_INFO("finished task " << i);
            });
        });
    }

    for (size_t periods = 0; pending_count; ++periods) {
        EXPECT_LT(periods, 20UL);
        POMAGMA_INFO("waiting " << periods);
        std::this_thread::sleep_for(std::chrono::milliseconds(max_wait));
    }
}

}  // namespace
}  // namespace pomagma
