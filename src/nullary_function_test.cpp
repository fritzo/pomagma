#include "nullary_function.hpp"
#include <vector>

using namespace pomagma;

void test_basic (size_t size)
{
    POMAGMA_INFO("Defining function");
    dense_set support(size);
    for (oid_t i = 1; i <= size; ++i) {
        if (random_bool(0.8)) {
            support.insert(i);
        }
    }
    NullaryFunction fun(support);
    fun.validate();

    fun.insert(1);
    fun.validate();
}

int main ()
{
    Log::title("Dense Nullary Function Test");

    for (size_t i = 0; i < 4; ++i) {
        test_basic(i + (1 << 9));
    }

    for (size_t exponent = 0; exponent < 10; ++exponent) {
        test_basic(1 << exponent);
    }

    return 0;
}
