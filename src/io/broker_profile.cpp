#include <pomagma/io/broker.hpp>
#include <thread>
#include <algorithm>

using namespace pomagma;

inline std::string random_message (rng_t & rng, size_t size = 16)
{
    std::string message(size, 0);
    std::generate_n(message.begin(), size, [&rng](){
        return "0123456789abcdef"[rng() % 16];
    });
    return message;
}

void profile_readers_writers (
        size_t topic_count,
        size_t worker_count,
        size_t message_count)
{
    POMAGMA_INFO("Broker: "
            << worker_count << " workers, "
            << topic_count << " topics");
    POMAGMA_ASSERT_EQ(0, message_count % worker_count);
    NaiveBroker broker(topic_count);
    for (size_t t = 0; t < topic_count; ++t) {
        broker.subscribe(t);
    }

    Timer timer;
    std::vector<std::thread> threads;

    // write to random topics
    for (size_t w = 0; w < worker_count; ++w) {
        threads.push_back(std::thread(
        [topic_count, worker_count, message_count, &broker, w](){
            rng_t rng(w);
            for (size_t m = 0; m < message_count / worker_count; ++m) {
                size_t topic = rng() % topic_count;
                broker.write(topic, random_message(rng));
            }
        }));
    }

    // read sequentially until topic is empty, then jump to another topic
    for (size_t w = 0; w < worker_count; ++w) {
        threads.push_back(std::thread(
        [topic_count, worker_count, message_count, &broker, w](){
            rng_t rng(w);
            std::string message;
            size_t topic = rng() % topic_count;
            for (size_t m = 0; m < message_count / worker_count; ++m) {
                if (not broker.try_read(topic, message)) {
                    topic = rng() % topic_count;
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

    profile_readers_writers(40000, 8, 1000000);

    return 0;
}
