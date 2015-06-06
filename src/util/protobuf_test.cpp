#include <pomagma/util/protobuf.hpp>
#include <pomagma/util/protobuf_test.pb.h>

using namespace pomagma;
using pomagma::protobuf::TestMessage;

void test_write_read (const TestMessage & expected)
{
    const std::string filename = "test.pb.gz";
    {
        protobuf::OutFile file(filename);
        file.write(expected);
    }
    TestMessage actual;
    {
        protobuf::InFile file(filename);
        file.read(actual);
    }
    POMAGMA_ASSERT_EQ(actual.ShortDebugString(), expected.ShortDebugString());
}

int main ()
{
    Log::Context log_context("Util Protobuf Test");

    POMAGMA_INFO("testing empty message");
    in_temp_dir([](){
        TestMessage message;
        test_write_read(message);
    });

    return 0;
}
