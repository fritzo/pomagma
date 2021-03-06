#include <pomagma/util/queue.hpp>
#include <thread>
#include <algorithm>

using namespace pomagma;

template <class Queue>
void profile_readers_writers(size_t topic_count, size_t worker_count,
                             size_t message_count) {
    POMAGMA_INFO(demangle(typeid(Queue).name()) << ": " << worker_count
                                                << " workers, " << topic_count
                                                << " topics");
    POMAGMA_ASSERT_EQ(0, message_count % worker_count);
    SharedBroker<Queue> broker(topic_count);

    Timer timer;
    std::vector<std::thread> threads;

    // write to random topics
    for (size_t w = 0; w < worker_count; ++w) {
        threads.push_back(std::thread([topic_count, worker_count, message_count,
                                       &broker, w]() {
            rng_t rng(w);
            std::uniform_int_distribution<> random_topic(0, topic_count - 1);
            std::uniform_int_distribution<> random_size(1, 255);
            const char* message =
                "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd"
                "ef"
                "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd"
                "ef"
                "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd"
                "ef"
                "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd"
                "ef";
            for (size_t m = 0; m < message_count / worker_count; ++m) {
                size_t topic = random_topic(rng);
                broker.push(topic, message, random_size(rng));
            }
        }));
    }

    // read sequentially until topic is empty, then jump to another topic
    for (size_t w = 0; w < worker_count; ++w) {
        threads.push_back(std::thread(
            [topic_count, worker_count, message_count, &broker, w]() {
                rng_t rng(w);
                std::uniform_int_distribution<> random_topic(0,
                                                             topic_count - 1);
                uint8_t message[256];
                size_t topic = random_topic(rng);
                for (size_t m = 0; m < message_count / worker_count; ++m) {
                    while (unlikely(not broker.try_pop(topic, &message))) {
                        topic = random_topic(rng);
                    }
                }
            }));
    }

    for (auto& thread : threads) {
        thread.join();
    }

    double rate_mhz = message_count / timer.elapsed() / 1e6;
    POMAGMA_INFO("processed " << rate_mhz << " messages/usec");
}

int main() {
    Log::Context log_context("Broker profile");

    profile_readers_writers<VectorQueue>(40000, 8, 1000000);

    // If we test with too many topics, this fails with:
    // boost::filesystem::unique_path: Too many open files
    profile_readers_writers<FileBackedQueue>(400, 8, 1000000);

    return 0;
}
