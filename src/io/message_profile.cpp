#include "message.hpp"
#include <pomagma/util/queue.hpp>
#include <thread>

using namespace pomagma;
using namespace pomagma::io;

typedef std::vector<uint32_t> Example;
std::vector<Example> examples =
{
    {0},
    {0,1,2,3,4,5,6,7,8,9},
    {1234, 567890, 1234567890, 12345678},
    {0, 0xFU, 0xFFU, 0xFFFU, 0xFFFFU},
    {0xFU, 0xFFU, 0xFFFU, 0xFFFFU, 0xFFFFFU},
    {0xFFFFFU, 0xFFFFFFU, 0xFFFFFFFU, 0xFFFFFFFFU},
    {0xFFFFFFU, 0xFFFFFFFU, 0xFFFFFFFFU},
    {0xFFFFFFFFU, 0xFFFFFFFFU, 0xFFFFFFFFU},
};

template<class Writer, class Reader, class... Args>
void write_read (const Example & example, std::string & message, Args... args)
{
    {
        Writer writer(message, args...);
        for (auto value : example) {
            writer.write(value);
        }
    }
    {
        Reader reader(message);
        for (auto expected : example) {
            uint32_t actual = reader.read();
            POMAGMA_ASSERT_EQ(actual, expected);
        }
    }
}

template<class Writer, class Reader>
void profile_inline (size_t message_count)
{
    Timer timer;

    std::string message;
    for (size_t i = 0; i < message_count; ++i) {
        const Example & example = examples[i % examples.size()];
        {
            Writer writer(message, example.size());
            for (auto value : example) {
                writer.write(value);
            }
        }
        Reader reader(message);
        for (auto expected : example) {
            uint32_t actual = reader.read();
            POMAGMA_ASSERT_EQ(actual, expected);
        }
    }

    double rate_mhz = message_count / timer.elapsed() / 1e6;
    POMAGMA_INFO(
        demangle(typeid(Writer).name()) << "-" <<
        demangle(typeid(Reader).name()) <<
        " processed " << rate_mhz << " messages/usec");
}

template<class Writer, class Reader>
void profile_queue (size_t message_count)
{
    Timer timer;
    VectorQueue queue;

    std::thread write_thread([message_count, &queue]{
        std::string message;
        for (size_t i = 0; i < message_count; ++i) {
            const Example & example = examples[i % examples.size()];
            Writer writer(message, example.size());
            for (auto value : example) {
                writer.write(value);
            }
            queue.push_str(message);
        }
    });
    std::thread read_thread([message_count, &queue]{
        std::string message;
        for (size_t i = 0; i < message_count; ++i) {
            while (not queue.try_pop_str(message)) {
                usleep(10);
            }
            Reader reader(message);
            for (auto expected : examples[i % examples.size()]) {
                uint32_t actual = reader.read();
                POMAGMA_ASSERT_EQ(actual, expected);
            }
        }
    });
    write_thread.join();
    read_thread.join();

    double rate_mhz = message_count / timer.elapsed() / 1e6;
    POMAGMA_INFO(
        demangle(typeid(Writer).name()) << "-" <<
        demangle(typeid(Reader).name()) <<
        " processed " << rate_mhz << " messages/usec");
}

int main ()
{
    Log::Context log_context("Message profile");

    size_t count = 1000000;

    POMAGMA_INFO("Inline write-read:");
    profile_inline<Int32Writer, Int32Reader>(count);
    profile_inline<Varint32Writer, Varint32Reader>(count);
    profile_inline<ProtobufVarint32Writer, ProtobufVarint32Reader>(count);

    POMAGMA_INFO("Queued write-read:");
    profile_queue<Int32Writer, Int32Reader>(count);
    profile_queue<Varint32Writer, Varint32Reader>(count);
    profile_queue<ProtobufVarint32Writer, ProtobufVarint32Reader>(count);

    return 0;
}
