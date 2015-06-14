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

void discard_digest (protobuf::OutFile &) {}
void discard_digest (protobuf::Sha1OutFile & file)
{
    POMAGMA_ASSERT(not file.hexdigest().empty(), "no digest found");
}

template<class OutFile>
void test_write_read (const TestMessage & expected)
{
    POMAGMA_INFO("Testing read o write");
    TestMessage actual;
    in_temp_dir([&](){
        const std::string filename = "test.pb";
        {
            OutFile file(filename);
            file.write(expected);
            discard_digest(file);
        }
        {
            protobuf::InFile file(filename);
            file.read(actual);
        }
    });
    POMAGMA_ASSERT_EQ(actual.ShortDebugString(), expected.ShortDebugString());
}

template<class OutFile>
void test_write_read_chunks (const TestMessage & expected)
{
    POMAGMA_INFO("Testing chunked read o write");
    TestMessage actual;
    in_temp_dir([&](){
        const std::string filename = "test.pb";
        {
            OutFile file(filename);
            file.write(expected);
            discard_digest(file);
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

template<class OutFile>
void test_digest (const TestMessage & message)
{
    POMAGMA_INFO("Testing digest");
    std::string actual;
    std::string expected;
    in_temp_dir([&](){
        const std::string filename = "test.pb";
        {
            OutFile file(filename);
            file.write(message);
            actual = get_digest(file);
        }
        expected = get_digest(filename);
    });
    POMAGMA_ASSERT_EQ(actual, expected);
}

void test (std::function<void(TestMessage &)> build_message)
{
    TestMessage message;
    build_message(message);
    POMAGMA_INFO("Testing with " << message.ShortDebugString().substr(0, 256));

    test_write_read<protobuf::OutFile>(message);
    test_write_read_chunks<protobuf::OutFile>(message);
    // TODO fix these
    //test_write_read<protobuf::Sha1OutFile>(message);
    //test_write_read_chunks<protobuf::Sha1OutFile>(message);
    //test_digest<protobuf::OutFile>(message);
    //test_digest<protobuf::Sha1OutFile>(message);
}

int main ()
{
    Log::Context log_context("Util Protobuf Test");

    test([](TestMessage & message){
        // This may actually fail for gzip streams, which need at least 6 bytes.
        // see google/protobuf/io/gzip_stream.h:171 about
        // GzipOutputStream::Flush
        message.Clear();
    });
    test([](TestMessage & message){
        message.set_optional_string("test");
    });
    test([](TestMessage & message){
        message.add_repeated_string("test1");
        message.add_repeated_string("test2");
    });
    test([](TestMessage & message){
        message.set_optional_string("test");
        message.add_repeated_string("test1");
        message.add_repeated_string("test2");
        auto & sub_message = * message.mutable_optional_message();
        sub_message.add_repeated_message()->set_optional_string("sub sub 1");
        sub_message.add_repeated_message()->add_repeated_string("sub sub 2");
        message.add_repeated_message()->set_optional_string("sub 1");
        message.add_repeated_message()->add_repeated_string("sub 2");
    });
    test([](TestMessage & message){
        message.set_optional_string("test");
        message.add_repeated_string("test1");
        message.add_repeated_string("test2");
        * message.mutable_optional_message() = TestMessage(message);
        for (size_t i = 0; i < 12; ++i) {
            * message.add_repeated_message() = TestMessage(message);
        }
        // this should be a big message to test Next, Backup, and Flush
        POMAGMA_ASSERT_LT(65536, message.ByteSize());
    });

    return 0;
}
