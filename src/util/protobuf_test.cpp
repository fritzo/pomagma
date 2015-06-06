#include <pomagma/util/protobuf.hpp>
#include <pomagma/util/protobuf_test.pb.h>

using namespace pomagma;
using pomagma::protobuf::TestMessage;

void test_write_read (const TestMessage & expected)
{
    POMAGMA_INFO("Testing read(write(" << expected.ShortDebugString() << "))");
    TestMessage actual;
    in_temp_dir([&](){
        const std::string filename = "test.pb.gz";
        {
            protobuf::OutFile file(filename);
            file.write(expected);
        }
        {
            protobuf::InFile file(filename);
            file.read(actual);
        }
    });
    POMAGMA_ASSERT_EQ(actual.ShortDebugString(), expected.ShortDebugString());
}

void test_write_read_chunks (const TestMessage & expected)
{
    POMAGMA_INFO("Testing read(write(" << expected.ShortDebugString() << "))");
    TestMessage actual;
    in_temp_dir([&](){
        const std::string filename = "test.pb.gz";
        {
            protobuf::OutFile file(filename);
            file.write(expected);
        }
        {
            protobuf::InFile file(filename);
            while (file.try_read_chunk(actual)) {
                POMAGMA_INFO("cumulative: " << actual.ShortDebugString());
            }
        }
    });
    POMAGMA_ASSERT_EQ(actual.ShortDebugString(), expected.ShortDebugString());
}

int main ()
{
    Log::Context log_context("Util Protobuf Test");

    {
        TestMessage message;
        test_write_read(message);
        test_write_read_chunks(message);
    }
    {
        TestMessage message;
        message.set_optional_string("test");
        test_write_read(message);
        test_write_read_chunks(message);
    }
    {
        TestMessage message;
        message.add_repeated_string("test1");
        message.add_repeated_string("test2");
        test_write_read(message);
        test_write_read_chunks(message);
    }
    {
        TestMessage message;
        message.set_optional_string("test");
        message.add_repeated_string("test1");
        message.add_repeated_string("test2");
        auto & sub_message = * message.mutable_optional_message();
        sub_message.add_repeated_message()->set_optional_string("sub sub 1");
        sub_message.add_repeated_message()->add_repeated_string("sub sub 2");
        message.add_repeated_message()->set_optional_string("sub 1");
        message.add_repeated_message()->add_repeated_string("sub 2");
        test_write_read(message);
        test_write_read_chunks(message);
    }

    return 0;
}
