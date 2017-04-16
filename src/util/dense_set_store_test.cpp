#include <gtest/gtest.h>
#include <pomagma/util/dense_set_store.hpp>
#include <unordered_set>
#include <vector>

namespace pomagma {
namespace {

using namespace ::pomagma::sequential;

rng_t rng;

std::string print_set(const DenseSet& set) {
    std::string result;
    for (size_t i = 1; i <= set.item_dim(); ++i) {
        result.push_back(set.contains(i) ? '+' : '-');
    }
    return result;
}

class DenseSetTest : public ::testing::TestWithParam<size_t>{};

TEST_P(DenseSetTest, StoreLoad) {
    const size_t item_dim = GetParam();
    const size_t element_count = 1000;

    POMAGMA_INFO("Testing store and load with size " << item_dim);

    DenseSetStore sets(item_dim);
    std::unordered_set<SetId> known_ids;

    for (size_t i = 0; i < element_count; ++i) {
        DenseSet set(item_dim);
        set.fill_random(rng);
        POMAGMA_DEBUG("insert " << print_set(set));
        set.validate();

        POMAGMA_ASSERT(not set.is_alias(), "programmer error");
        SetId id = sets.store(std::move(set));
        if (known_ids.insert(id).second) {
            POMAGMA_ASSERT(set.is_alias(), "data was not moved");
            POMAGMA_ASSERT(sets.load(id).raw_data() == set.raw_data(),
                           "inserted pointer does not match source");
        } else {
            POMAGMA_ASSERT(not set.is_alias(),
                           "data freed but set not inserted");
        }

        const DenseSet loaded1 = sets.load(id);
        POMAGMA_ASSERT(loaded1.is_alias(), "loaded set is not alias");
        loaded1.validate();
        const DenseSet loaded2 = sets.load(id);
        POMAGMA_ASSERT(loaded1.raw_data() == loaded2.raw_data(),
                       "two loads disagree");
        if (loaded1 != set) {
            POMAGMA_WARN("expected: " << print_set(set));
            POMAGMA_WARN("actual: " << print_set(loaded1));
            POMAGMA_WARN("id: " << id);
            POMAGMA_ERROR("loaded does not match stored");
        }

        POMAGMA_ASSERT(id == sets.store(std::move(set)), "two stores disagree");
    }
}

INSTANTIATE_TEST_CASE_P(AllDims, DenseSetTest, ::testing::Range(1UL, 128UL));

}  // namespace
}  // namespace pomagma
