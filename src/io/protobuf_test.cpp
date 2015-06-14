#include <pomagma/io/protobuf.hpp>
#include <pomagma/io/protobuf_test.pb.h>

using namespace pomagma;
using pomagma::protobuf::TestMessage;

std::string get_digest (const std::string & filename)
{
    Hasher hasher;
    hasher.add_file(filename);
    hasher.finish();
    return hasher.str();
}

std::string get_digest (protobuf::OutFile & file)
{
    file.flush();
    return get_digest(file.filename());
}

std::string get_digest (protobuf::Sha1OutFile & file)
{
    return file.hexdigest();
}

template<class OutFile>
void test_write_read (const TestMessage & expected)
{
    POMAGMA_INFO("Testing read(write(" << expected.ShortDebugString() << "))");
    TestMessage actual;
    std::string actual_digest;
    std::string expected_digest;
    in_temp_dir([&](){
        const std::string filename = "test.pb";
        {
            OutFile file(filename);
            file.write(expected);
            actual_digest = get_digest(file);
        }
        expected_digest = get_digest(filename);
        {
            protobuf::InFile file(filename);
            file.read(actual);
        }
    });
    POMAGMA_ASSERT_EQ(actual.ShortDebugString(), expected.ShortDebugString());
    // POMAGMA_ASSERT_EQ(actual_digest, expected_digest);  // FIXME
}

template<class OutFile>
void test_write_read_chunks (const TestMessage & expected)
{
    POMAGMA_INFO("Testing read(write(" << expected.ShortDebugString() << "))");
    TestMessage actual;
    std::string actual_digest;
    std::string expected_digest;
    in_temp_dir([&](){
        const std::string filename = "test.pb";
        {
            OutFile file(filename);
            file.write(expected);
            actual_digest = get_digest(file);
        }
        expected_digest = get_digest(filename);
        {
            protobuf::InFile file(filename);
            while (file.try_read_chunk(actual)) {
                POMAGMA_INFO("cumulative: " << actual.ShortDebugString());
            }
        }
    });
    POMAGMA_ASSERT_EQ(actual.ShortDebugString(), expected.ShortDebugString());
    // POMAGMA_ASSERT_EQ(actual_digest, expected_digest);  // FIXME
}

void test (const TestMessage & message)
{
    test_write_read<protobuf::OutFile>(message);
    test_write_read<protobuf::Sha1OutFile>(message);
    test_write_read_chunks<protobuf::OutFile>(message);
    test_write_read_chunks<protobuf::Sha1OutFile>(message);
}

int main ()
{
    Log::Context log_context("Util Protobuf Test");

    {
        // This may actually fail for gzip streams, which need at least 6 bytes.
        // see google/protobuf/io/gzip_stream.h:171 about
        // GzipOutputStream::Flush
        TestMessage message;
        test(message);
    }
    {
        TestMessage message;
        message.set_optional_string("test");
        test(message);
    }
    {
        TestMessage message;
        message.add_repeated_string("test1");
        message.add_repeated_string("test2");
        test(message);
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
        test(message);
    }

    return 0;
}
