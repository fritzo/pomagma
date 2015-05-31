#include <pomagma/platform/util.hpp>

using namespace pomagma;

void test_endswith ()
{
    POMAGMA_INFO("Testing endswith(-,-)");

    POMAGMA_ASSERT_EQ(endswith("", ""), true);
    POMAGMA_ASSERT_EQ(endswith("asdf", ""), true);
    POMAGMA_ASSERT_EQ(endswith("asdf", "f"), true);
    POMAGMA_ASSERT_EQ(endswith("asdf", "d"), false);
    POMAGMA_ASSERT_EQ(endswith("asdf", ".gz"), false);
    POMAGMA_ASSERT_EQ(endswith("asdf.gz", ".gz"), true);
}

int main ()
{
    Log::Context log_context("Running Util Test");

    test_endswith();

    return 0;
}
