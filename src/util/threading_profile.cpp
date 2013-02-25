#include <pomagma/util/threading.hpp>
#include <thread>
#include <future>
#include <tbb/concurrent_queue.h>

using namespace pomagma;


void task (size_t)
{
    memory_barrier();
}


std::atomic<bool> g_alive(false);
tbb::concurrent_queue<size_t> g_work_queue;
static std::mutex g_work_mutex;
static std::condition_variable g_work_condition;

void schedule (size_t i)
{
    g_work_queue.push(i);
    g_work_condition.notify_one();

    std::unique_lock<std::mutex> lock(g_work_mutex);
    while (not g_work_queue.empty()) {
        g_work_condition.wait(lock);
    }
}

void do_work ()
{
    while (g_alive) {
        size_t i;
        std::unique_lock<std::mutex> lock(g_work_mutex);
        if (g_work_queue.try_pop(i)) {
            task(i);
            g_work_condition.notify_one();
        } else {
            g_work_condition.wait(lock);
        }
    }
}


template<class Function>
void print_rate (std::string name, Function function)
{
    size_t iters = 0;
    size_t block = 1000;
    float duration = 0.5;
    Timer timer;
    float rate;
    while (true) {
        for (size_t i = 0; i < block; ++i) {
            function(i);
        }
        iters += block;
        float time = timer.elapsed();
        if (time > duration) {
            rate = iters / timer.elapsed();
            break;
        }
    }

    POMAGMA_INFO(std::setw(12) << name << std::setw(12) << rate);
}

int main ()
{
    Log::title("Threading profile");

    print_rate("call", [&](size_t i){
        task(i);
    });

    print_rate("spawn", [&](size_t i){
        std::thread(task, i).join();
    });

    print_rate("async", [&](size_t i){
        std::async(std::launch::async, task, i).wait();
    });

    g_alive = true;
    std::thread worker(do_work);
    print_rate("pool", [&](size_t i){
        schedule(i);
    });
    g_alive = false;
    g_work_condition.notify_one();
    worker.join();

    return 0;
}
