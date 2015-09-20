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

        SetId id;
        {
            DenseSet copy(item_dim);
            copy = set;
            copy.validate();
            POMAGMA_ASSERT(copy == set, "programmer error");
            const Word * data = copy.raw_data();
            id = sets.store(std::move(copy));
            POMAGMA_ASSERT(copy.raw_data() == nullptr, "data not freed");
            if (known_ids.insert(id).second) {
                POMAGMA_ASSERT(sets.load(id).raw_data() == data,
                    "data was not moved");
            }
        }
        {
            const DenseSet loaded1 = sets.load(id);
            const DenseSet loaded2 = sets.load(id);
            loaded1.validate();
            POMAGMA_ASSERT(loaded1.raw_data() == loaded2.raw_data(),
                "two loads disagree");
#if 0  // FIXME
            if (loaded1 != set) {
                POMAGMA_WARN("expected: " << print_set(set));
                POMAGMA_WARN("actual: " << print_set(loaded1));
                POMAGMA_WARN("id: " << id);
                POMAGMA_ERROR("loaded does not match stored");
            }
#endif  // FIXME
        }
        POMAGMA_ASSERT(id == sets.store(std::move(set)), "two stores disagree");
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
