#include <gtest/gtest.h>
#include <pomagma/util/util.hpp>
#include <pomagma/util/lazy_map.hpp>

namespace pomagma {
namespace {

typedef const std::pair<int, int>* Key;
typedef int Value;

TEST(LazyMapTest, IsCorrect) {
    const size_t eval_count = 100;
    const size_t max_wait = 100;

    WorkerPool worker_pool;
    LazyMap<Key, Value> lazy_map(worker_pool, [](const Key& key) {
        Value value = 1 + key->first + key->second;
        std::this_thread::sleep_for(std::chrono::milliseconds(value));
        return value;
    });

    rng_t rng;
    std::uniform_int_distribution<> random_int(0, max_wait);

    std::atomic<uint_fast64_t> pending_count(eval_count);

    for (size_t i = 0; i < eval_count; ++i) {
        POMAGMA_INFO("starting task " << i);
        Key key = new std::pair<int, int>(random_int(rng), random_int(rng));
        auto delay = std::chrono::milliseconds(random_int(rng));
        new std::thread([delay, &lazy_map, key, &pending_count, i] {
            do {
                std::this_thread::sleep_for(delay);
            } while (not lazy_map.try_find(key));
            --pending_count;
            POMAGMA_INFO("finished task " << i);
        });
    }

    for (size_t periods = 0; pending_count; ++periods) {
        EXPECT_LT(periods, eval_count);
        POMAGMA_INFO("waiting " << periods);
        std::this_thread::sleep_for(std::chrono::milliseconds(max_wait));
    }
}

}  // namespace
}  // namespace pomagma
