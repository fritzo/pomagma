#include "nullary_function.hpp"
#include <vector>

using namespace pomagma;

rng_t rng;

void test_basic (size_t size)
{
    POMAGMA_INFO("Defining function");
    Carrier carrier(size);
    for (Ob i = 1; i <= size; ++i) {
        POMAGMA_ASSERT(carrier.unsafe_insert(), "insertion failed");
    }
    size_t item_count = size;
    std::bernoulli_distribution randomly_remove(0.2);
    for (Ob i = 1; i <= size and item_count > 1; ++i) {
        if (randomly_remove(rng)) {
            carrier.unsafe_remove(i);
            --item_count;
        }
    }

    NullaryFunction fun(carrier);
    fun.validate();

    Ob ob = 1;
    while (not carrier.contains(ob)) {
        ++ob;
    }
    fun.insert(ob);
    fun.validate();

    POMAGMA_ASSERT(fun.defined(), "nullary function has nothing to clear");
    fun.clear();
    fun.validate();
    POMAGMA_ASSERT(not fun.defined(), "nullary function was not cleared");
}

int main ()
{
    Log::Context log_context("Dense Nullary Function Test");

    for (size_t i = 0; i < 4; ++i) {
        test_basic(i + (1 << 9));
    }

    for (size_t exponent = 0; exponent < 10; ++exponent) {
        test_basic(1 << exponent);
    }

    return 0;
}
