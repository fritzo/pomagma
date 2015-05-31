#include "stream.hpp"
#include <cstdio>

using namespace pomagma;

void test_dump_load (const char * filename)
{
    std::vector<std::vector<char>> expected = {
        {},
        {'a'},
        {'b', 'c'},
        {},
        {'d'}
    };
    POMAGMA_INFO("dumping to " << filename);
    protobuf_stream_dump(expected, filename);
    POMAGMA_INFO("loading from " << filename);
    auto actual = protobuf_stream_load<std::vector<char>>(filename);
    std::remove(filename);
    POMAGMA_ASSERT_EQ(actual, expected);
}

int main ()
{
    Log::Context log_context("Running Protobuf Stream Test");

    test_dump_load("/tmp/protobuf_stream_test.pbs");
    test_dump_load("/tmp/protobuf_stream_test.pbs.gz");

    return 0;
}
