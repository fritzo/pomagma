#include <gtest/gtest.h>

#include <pomagma/util/hasher.hpp>

using namespace pomagma;

const std::string examples[] = {
    "0000000000000000000000000000000000000000",
    "0123456789abcdef0123456789abcdef01234567",
    "123456789abcdef0123456789abcdef012345678",
    "23456789abcdef0123456789abcdef0123456789",
    "3456789abcdef0123456789abcdef0123456789a",
    "456789abcdef0123456789abcdef0123456789ab",
    "56789abcdef0123456789abcdef0123456789abc",
    "6789abcdef0123456789abcdef0123456789abcd",
    "789abcdef0123456789abcdef0123456789abcde",
    "89abcdef0123456789abcdef0123456789abcdef",
};

TEST(PrintParseHashTest, ParseAndPrintDigest) {
    POMAGMA_INFO("Testing parse_digest and print_digest");
    for (const auto& expected : examples) {
        Hasher::Digest digest = parse_digest(expected);
        std::string actual = print_digest(digest);
        EXPECT_EQ(actual, expected);
    }
}
