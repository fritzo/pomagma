#include <google/protobuf/text_format.h>
#include <pomagma/io/protobuf.hpp>
#include <pomagma/io/protobuf_test.pb.h>
#include <string>
#include <vector>

using google::protobuf::TextFormat;
using namespace pomagma;
using pomagma::protobuf::TestMessage;

TestMessage parse(const std::string& text) {
    TestMessage message;
    POMAGMA_ASSERT(TextFormat::ParseFromString(text, &message), "parse error");
    return message;
}

TestMessage make_big_message(size_t depth = 12) {
    TestMessage message = parse(R"(
        optional_string: 'test'
        repeated_string: 'test1'
        repeated_string: 'test2'
        repeated_message: {
            repeated_string: 'sub 2'
        }
    )");
    *message.mutable_optional_message() = TestMessage(message);
    for (size_t i = 0; i < depth; ++i) {
        *message.add_repeated_message() = TestMessage(message);
    }
    // this should be a big message to test Next and Backup
    POMAGMA_ASSERT_LT(65536, message.ByteSize());
    return message;
}

const std::vector<TestMessage> g_examples = {
    // The empty message may actually fail for gzip streams, which need at
    // least 6 bytes. see google/protobuf/io/gzip_stream.h:171 about
    // GzipOutputStream::Flush
    parse(""), parse(R"(
        optional_string: 'test'
    )"),
    parse(R"(
        repeated_string: 'test1'
        repeated_string: 'test2'
    )"),
    parse(R"(
        optional_string: 'test'
        repeated_string: 'test1'
        repeated_string: 'test2'
        optional_message: {
            repeated_message: {}
            repeated_message: {
                optional_string: 'sub sub 1'
                repeated_string: 'sub'
            }
            repeated_message: {
                optional_string: 'sub 1'
            }
            repeated_message: {
                repeated_string: 'sub 2'
            }
        }
    )"),
    make_big_message()};

std::string get_digest(const std::string& filename) {
    Hasher hasher;
    hasher.add_file(filename);
    hasher.finish();
    return hasher.str();
}

std::string get_digest_and_delete(protobuf::OutFile* file) {
    std::string filename = file->filename();
    delete file;
    return get_digest(filename);
}

std::string get_digest_and_delete(protobuf::Sha1OutFile* file) {
    std::string digest = file->hexdigest();
    delete file;
    return digest;
}

void discard_digest(protobuf::OutFile&) {}
void discard_digest(protobuf::Sha1OutFile& file) {
    POMAGMA_ASSERT(not file.hexdigest().empty(), "no digest found");
}

template <class OutFile>
void test_write_read(const TestMessage& expected) {
    POMAGMA_INFO("Testing read o write");
    TestMessage actual;
    in_temp_dir([&]() {
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

template <class OutFile>
void test_write_read_chunks(const TestMessage& expected) {
    POMAGMA_INFO("Testing chunked read o write");
    TestMessage actual;
    in_temp_dir([&]() {
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

template <class OutFile>
void test_digest(const TestMessage& message) {
    POMAGMA_INFO("Testing digest");
    std::string actual;
    std::string expected;
    in_temp_dir([&]() {
        const std::string filename = "test.pb";
        {
            OutFile* file = new OutFile(filename);
            file->write(message);
            actual = get_digest_and_delete(file);
        }
        expected = get_digest(filename);
    });
    POMAGMA_ASSERT_EQ(actual, expected);
}

int main() {
    Log::Context log_context("Util Protobuf Test");

    for (const auto& message : g_examples) {
        POMAGMA_INFO("Testing with "
                     << message.ShortDebugString().substr(0, 256));
        test_write_read<protobuf::OutFile>(message);
        test_write_read_chunks<protobuf::OutFile>(message);
        test_write_read<protobuf::Sha1OutFile>(message);
        test_write_read_chunks<protobuf::Sha1OutFile>(message);
        test_digest<protobuf::OutFile>(message);
        test_digest<protobuf::Sha1OutFile>(message);
    }

    return 0;
}
