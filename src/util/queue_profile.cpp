#include <pomagma/util/queue.hpp>
#include <thread>
#include <algorithm>

using namespace pomagma;

inline std::string random_message (
        rng_t & rng,
        size_t min_size,
        size_t max_size)
{
    std::uniform_int_distribution<> random_size(min_size, max_size);
    size_t size = random_size(rng);
    std::string message(size, 0);
    std::generate_n(message.begin(), size, [&rng](){
        return "0123456789abcdef"[rng() % 16];
    });
    return message;
}

template<class Queue>
void profile_readers_writers (
        size_t queue_count,
        size_t worker_count,
        size_t message_count)
{
    POMAGMA_INFO(demangle(typeid(Queue).name()) << ": "
        << worker_count << " workers, "
        << queue_count << " queues");
    POMAGMA_ASSERT_EQ(0, message_count % worker_count);
    SharedBroker<Queue> broker(queue_count);

    Timer timer;
    std::vector<std::thread> threads;

    // write to random queues
    for (size_t w = 0; w < worker_count; ++w) {
        threads.push_back(std::thread(
        [queue_count, worker_count, message_count, &broker, w](){
            rng_t rng(w);
            std::uniform_int_distribution<> random_queue(0, queue_count - 1);
            for (size_t m = 0; m < message_count / worker_count; ++m) {
                size_t queue_id = random_queue(rng);
                std::string message = random_message(rng, 1, 255);
                broker.push(queue_id, message.data(), message.size());
            }
        }));
    }

    // read sequentially until queue is empty, then jump to another queue
    for (size_t w = 0; w < worker_count; ++w) {
        threads.push_back(std::thread(
        [queue_count, worker_count, message_count, &broker, w](){
            rng_t rng(w);
            std::uniform_int_distribution<> random_queue(0, queue_count - 1);
            uint8_t message[256];
            size_t queue = random_queue(rng);
            for (size_t m = 0; m < message_count / worker_count; ++m) {
                while (unlikely(not broker.try_pop(queue, &message))) {
                    queue = random_queue(rng);
                }
            }
        }));
    }

    for (auto & thread : threads) {
        thread.join();
    }

    double rate_mhz = message_count / timer.elapsed() / 1e6;
    POMAGMA_INFO("processed " << rate_mhz << " messages/usec");
}

int main ()
{
    Log::Context log_context("Broker profile");

    profile_readers_writers<VectorQueue>(40000, 8, 1000000);

    // FIXME this is broken
    // profile_readers_writers<PagedQueue>(40000, 8, 1000000);

    return 0;
}
