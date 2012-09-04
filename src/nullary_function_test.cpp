#include "nullary_function.hpp"
#include <vector>

using namespace pomagma;

void test_basic (size_t size)
{
    POMAGMA_INFO("Defining function");
    Carrier carrier(size);
    for (Ob i = 1; i <= size; ++i) {
        carrier.insert();
    }
    size_t item_count = size;
    for (Ob i = 1; i <= size and item_count > 1; ++i) {
        if (random_bool(0.2)) {
            carrier.remove(i);
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
