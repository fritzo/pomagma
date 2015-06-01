#include <pomagma/util/util.hpp>
#include <pomagma/util/async_map.hpp>
#include <pomagma/util/worker_pool.hpp>

using namespace pomagma;

namespace test
{

typedef const std::pair<int, int> * Key;
typedef int Value;

typedef AsyncMap<Key, Value> Cache;

struct Task
{
    Key key;
    Cache::Callback callback;
};

struct Processor
{
    void operator() (Task & task)
    {
        Value * value = new Value(task.key->first + task.key->second);
        std::this_thread::sleep_for(std::chrono::milliseconds(* value));
        task.callback(value);
    }
};

struct AsyncFunction
{
    WorkerPool<Task, Processor> & pool;

    void operator() (Key key, Cache::Callback callback)
    {
        pool.schedule(Task({key, callback}));
    }
};

void async_map_test (
    size_t thread_count,
    size_t eval_count,
    size_t max_wait = 100)
{
    Processor processor;
    WorkerPool<Task, Processor> pool(processor, thread_count);
    AsyncFunction function({pool});
    Cache cache(function);

    std::random_device device;
    rng_t rng(device());
    std::uniform_int_distribution<> random_int(0, max_wait);

    std::atomic<uint_fast64_t> pending_count(eval_count);

    for (size_t i = 0; i < eval_count; ++i) {
        POMAGMA_INFO("starting task " << i);
        Key key = new std::pair<int, int>(random_int(rng), random_int(rng));
        auto delay = std::chrono::milliseconds(random_int(rng));
        new std::thread([delay, &cache, key, &pending_count, i](){
            std::this_thread::sleep_for(delay);
            cache.find_async(key, [&pending_count, i](const Value *){
                --pending_count;
                POMAGMA_INFO("finished task " << i);
            });
        });
    }

    for (size_t periods = 0; pending_count; ++periods) {
        POMAGMA_ASSERT_LT(periods, 20);
        POMAGMA_INFO("waiting " << periods);
        std::this_thread::sleep_for(std::chrono::milliseconds(max_wait));
    }
}

} // namespace test

int main ()
{
    test::async_map_test(10, 100);

    return 0;
}
