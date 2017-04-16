#include <pomagma/util/util.hpp>
#include <gtest/gtest.h>

int main(int argc, char **argv) {
  testing::InitGoogleTest(&argc, argv);
  pomagma::Log::Context log_context(argc, argv);
  return RUN_ALL_TESTS();
}
