#include "carrier.hpp"

using namespace pomagma;

rng_t rng;

void test_random (size_t size)
{
    Carrier carrier(size);
    carrier.validate();

    for (size_t i = 1; i <= size; ++i) {
        POMAGMA_ASSERT_EQ(carrier.try_insert(), i);
        carrier.validate();
    }

    std::uniform_int_distribution<size_t> random_ob(1, size);
    for (size_t i = 1; i <= size; ++i) {
        Ob dep = random_ob(rng);
        Ob rep = random_ob(rng);
        if (dep > rep) {
            carrier.merge(dep, rep);
        }
        carrier.validate();

        Ob ob = random_ob(rng);
        carrier.find(ob);
        carrier.validate();
    }

    std::bernoulli_distribution randomly_remove(0.5);
    for (size_t i = 1; i <= size; ++i) {
        if (randomly_remove(rng)) {
            if (carrier.contains(i) and carrier.find(i) != i) {
                carrier.unsafe_remove(i);
            }
            carrier.validate();
        }
    }

    carrier.clear();
    carrier.validate();
    POMAGMA_ASSERT_EQ(carrier.item_count(), 0);
}

int main ()
{
    Log::title("Carrier Test");

    POMAGMA_INFO("Testing random carrier");
    for (size_t size = 2; size < 200; ++size) {
        test_random(size);
    }

    return 0;
}
