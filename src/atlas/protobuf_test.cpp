#include <pomagma/atlas/protobuf.hpp>

using namespace pomagma;

typedef uint32_t Ob;

struct SparseMap
{
    std::vector<Ob> key;
    std::vector<Ob> val;
};

const std::vector<SparseMap> g_examples = {
    {{}, {}},
    {{1}, {9999}},
    {{1, 2, 3, 4}, {83, 212, 12345, 1}},
    {{1,99,999,9999, 99999}, {2, 22222, 22, 2222, 222}}
};

protobuf::SparseMap make_proto (const SparseMap& example)
{
    POMAGMA_ASSERT(example.key.size() == example.val.size(),
        "error in test data");
    protobuf::SparseMap message;
    for (auto key : example.key) { message.add_key(key); }
    for (auto val : example.val) { message.add_val(val); }
    return message;
}

void test_compress_decompress (const SparseMap& example)
{
    const auto expected = make_proto(example);
    POMAGMA_INFO("Compressing " << expected.ShortDebugString());
    auto actual = expected;
    compress_sparse_map(actual);
    decompress_sparse_map(actual);
    POMAGMA_ASSERT_EQ(actual.ShortDebugString(), expected.ShortDebugString());
}

void test_decompress_on_uncompressed_data (const SparseMap& example)
{
    const auto expected = make_proto(example);
    POMAGMA_INFO("Preserving " << expected.ShortDebugString());
    auto actual = expected;
    decompress_sparse_map(actual);
    POMAGMA_ASSERT_EQ(actual.ShortDebugString(), expected.ShortDebugString());
}

int main ()
{
    Log::Context log_context("Atlas Protobuf Test");

    for (const auto& example : g_examples) {
        test_compress_decompress(example);
        test_decompress_on_uncompressed_data(example);
    }

    return 0;
}
