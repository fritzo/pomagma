#include "message.hpp"
#include <vector>

using namespace pomagma;
using namespace pomagma::io;

std::vector<std::vector<uint32_t>> examples =
{
    {},
    {0},
    {0xFU},
    {0xFFU},
    {0xFFFU},
    {0xFFFFU},
    {0xFFFFFU},
    {0xFFFFFFU},
    {0xFFFFFFFU},
    {0xFFFFFFFFU},
    {0,1,2,3,4,5,6,7,8,9},
    {0xFFFFFFFFU, 0xFFFFFFFFU, 0xFFFFFFFFU},
    {0, 0xFU, 0xFFU, 0xFFFU, 0xFFFFU,
        0xFFFFFU, 0xFFFFFFU, 0xFFFFFFFU, 0xFFFFFFFFU},
    {1234, 567890, 1234567890, 12345678},
};

template<class Writer, class Reader, class... Args>
void test_write_read (const std::vector<uint32_t> & example, Args... args)
{
    POMAGMA_INFO("Testing " << demangle(typeid(Writer).name()) <<
        " and " << demangle(typeid(Writer).name()));

    std::string message;
    {
        Writer writer(message, args...);
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

int main ()
{
    Log::Context log_context("Atlas Message Test");

    for (const auto example : examples) {
        POMAGMA_INFO("Example: " << example);
        test_write_read<Int32Writer, Int32Reader>(example);
        // FIXME
        //test_write_read<Varint32Writer, Varint32Reader>(example);
        test_write_read<ProtobufVarint32Writer, ProtobufVarint32Reader>(
            example,
            example.size());
    }

    return 0;
}
