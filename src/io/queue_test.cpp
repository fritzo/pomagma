#include <atomic>
#include <pomagma/io/queue.hpp>
#include <thread>
#include <typeinfo>

using namespace pomagma;

void writer_thread (
        pomagma::ConcurrentQueue * queue,
        std::string message,
        size_t message_count,
        std::atomic<uint_fast64_t> * worker_count)
{
    POMAGMA_INFO("sending " << message_count << " messages");
    for (size_t i = 0; i < message_count; ++i) {
        queue->push(message.data(), message.size());
        if (i % 100 == 0) {
            usleep(10);
        }
    }
    --*worker_count;
}

template<class Queue>
void test_queue (Queue & queue)
{
    POMAGMA_INFO("Testing " << demangle(typeid(Queue).name()));

    const size_t message_count = 10000;

    std::vector<std::thread> threads;
    std::atomic<uint_fast64_t> worker_count(6);

    threads.push_back(std::thread(
        & writer_thread,
        & queue,
        "test",
        message_count,
        & worker_count));

    threads.push_back(std::thread(
        & writer_thread,
        & queue,
        "test-test-test-test-test-test-test-test-test-test-test-test-test",
        message_count,
        & worker_count));

    threads.push_back(std::thread(
        & writer_thread,
        & queue,
        "t",
        message_count,
        & worker_count));

    threads.push_back(std::thread(
        & writer_thread,
        & queue,
        "e",
        message_count,
        & worker_count));

    threads.push_back(std::thread(
        & writer_thread,
        & queue,
        "s",
        message_count,
        & worker_count));

    threads.push_back(std::thread(
        & writer_thread,
        & queue,
        "yet-another-test",
        message_count,
        & worker_count));

    size_t actual_message_count = 0;
    char message[Queue::max_message_size + 1];
    while (worker_count) {
        POMAGMA_INFO("receiving...");
        usleep(10);
        while (size_t size = queue.try_pop(message)) {
            message[size] = 0;
            POMAGMA_INFO("received: " << message);
            ++actual_message_count;
        }
    }
    POMAGMA_INFO("received " << actual_message_count << " messages");
    POMAGMA_ASSERT_EQ(actual_message_count, 6 * message_count);

    for (auto & thread : threads) { thread.join(); }
}

int main ()
{
    Log::Context log_context("Queue Test");

    {
        pomagma::VectorQueue queue;
        test_queue(queue);
    }
    {
        pomagma::FileBackedQueue queue("/tmp/pomagma_io_queue_test");
        test_queue(queue);
    }
    if (0) { // FIXME this fails
        pomagma::PagedQueue queue;
        test_queue(queue);
    }

    return 0;
}
