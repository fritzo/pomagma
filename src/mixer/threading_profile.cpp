#include "threading.hpp"
#include <thread>
#include <future>

using namespace pomagma;

void task ()
{
    memory_barrier();
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
            function();
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

    print_rate("call", [&](){
        task();
    });

    print_rate("spawn", [&](){
        std::thread(task).join();
    });

    print_rate("async", [&](){
        std::async(std::launch::async, task).wait();
    });

    // TODO time thread pool
    //std::thread worker(do_work);
    //print_rate("pool", [&](){
    //    pool_task();
    //});
    //g_alive = false;
    //worker.join();

    return 0;
}
