#include <pomagma/util/dense_set_store.hpp>
#include <vector>
#include <unordered_set>

using namespace pomagma;
using namespace sequential;

rng_t rng;

std::string print_set (const DenseSet & set)
{
    std::string result;
    for (size_t i = 1; i <= set.item_dim(); ++i) {
        result.push_back(set.contains(i) ? '+' : '-');
    }
    return result;
}

void test_store_load (size_t item_dim, size_t element_count)
{
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
        } else {
            POMAGMA_ASSERT(not set.is_alias(),
                "data freed but set not inserted");
        }

        const DenseSet loaded1 = sets.load(id);
        POMAGMA_ASSERT(loaded1.is_alias(), "loaded set is not alias");
#ifdef DENSE_SET_STORE_BUG_IS_FIXED
        loaded1.validate(); // FIXME segfault
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
#endif // DENSE_SET_STORE_BUG_IS_FIXED
    }
}

int main ()
{
    Log::Context log_context("DenseSetStore Test");

    for (size_t item_dim = 1; item_dim < 128; ++item_dim) {
        test_store_load(item_dim, 1000);
    }

    return 0;
}
