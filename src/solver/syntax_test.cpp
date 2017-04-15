#include <gtest/gtest.h>
#include <pomagma/solver/syntax.hpp>
#include <tuple>
#include <utility>

namespace pomagma {
namespace solver {
namespace {

// Test data.
static const unsigned example_ivar[] = {0, 1, 2, 3, 4, 5, 10, 100};
static const std::string example_nvar[] = {
    "a", "b", "x", "y", "unit", "a_very_long_variable_name",
};

unsigned random_rank(rng_t& rng) {
    static std::uniform_int_distribution<> random_index(
        0, sizeof(example_ivar) / sizeof(example_ivar[0]) - 1);
    return example_ivar[random_index(rng)];
}

std::string random_name(rng_t& rng) {
    static std::uniform_int_distribution<> random_index(
        0, sizeof(example_nvar) / sizeof(example_nvar[0]) - 1);
    return example_nvar[random_index(rng)];
}

Term add_random_term(Structure& structure, rng_t& rng) {
    // Switch on arity from {APP, JOIN, IVAR, NVAR}.
    static std::discrete_distribution<> random_arity({0.6, 0.2, 0.1, 0.1});
    switch (random_arity(rng)) {
        case 0: {
            const Term lhs = structure.choose_random_term(rng);
            const Term rhs = structure.choose_random_term(rng);
            return structure.app(lhs, rhs);
        }
        case 1: {
            const Term lhs = structure.choose_random_term(rng);
            const Term rhs = structure.choose_random_term(rng);
            return structure.join(lhs, rhs);
        }
        case 2: {
            const unsigned rank = random_rank(rng);
            return structure.ivar(rank);
        }
        case 3: {
            const std::string name = random_name(rng);
            return structure.nvar(name);
        }
        default: POMAGMA_ERROR("unreachable");
    }
}

TEST(StructureTest, ValidIfEmpty) {
    Structure structure;
    structure.assert_valid();
}

TEST(StructureTest, ValidAfterAddingIvar) {
    Structure structure;
    for (const auto ivar : example_ivar) {
        structure.ivar(ivar);
    }
    structure.assert_valid();
}

TEST(StructureTest, ValidAfterAddingNvar) {
    Structure structure;
    for (const auto nvar : example_ivar) {
        structure.ivar(nvar);
    }
    structure.assert_valid();
}

class RandomStructureTest : public ::testing::TestWithParam<int> {};

TEST_P(RandomStructureTest, IsValid) {
    const int term_count = 1000;
    const int seed = GetParam();
    rng_t rng(seed);
    Structure structure;

    // Randomly add terms.
    Term max_term = 0;
    for (int i = 0; i < term_count; ++i) {
        const Term term = add_random_term(structure, rng);
        max_term = std::max(max_term, term);
    }
    structure.assert_valid();

    // Randomly add literals.
    for (int i = 0; i < 10 * term_count; ++i) {
        const Term x = structure.choose_random_term(rng);
        const Term y = structure.choose_random_term(rng);
        (i % 2) ? structure.less(x, y) : structure.nless(y, x);
    }
    structure.assert_valid();

    // Make sure random data generators are sufficiently diverse.
    // This tests the testing tools.
    std::unordered_map<int, int> arity_histogram;
    for (Term term = 1; term <= max_term; ++term) {
        arity_histogram[static_cast<int>(structure.term_arity(term))] += 1;
    }
    EXPECT_LT(5, arity_histogram[static_cast<int>(TermArity::IVAR)]);
    EXPECT_LT(5, arity_histogram[static_cast<int>(TermArity::NVAR)]);
    EXPECT_LT(term_count / 10,
              arity_histogram[static_cast<int>(TermArity::APP)]);
    EXPECT_LT(term_count / 10,
              arity_histogram[static_cast<int>(TermArity::JOIN)]);

    // Check algebraic properties of join.
    for (int i = 0; i < term_count; ++i) {
        const Term x = structure.choose_random_term(rng);
        const Term y = structure.choose_random_term(rng);
        EXPECT_EQ(x, structure.join(x, x)) << "Failed JOIN idempotence";
        EXPECT_EQ(structure.join(x, y), structure.join(y, x))
            << "Failed JOIN commutativity";
    }
}

INSTANTIATE_TEST_CASE_P(AllSeeds, RandomStructureTest,
                        ::testing::Values(0, 1, 2, 3, 4));

}  // namespace
}  // namespace solver
}  // namespace pomagma
