#include "carrier.hpp"

using namespace pomagma;

void test_random (size_t size)
{
    Carrier carrier(size);
    carrier.validate();

    for (size_t i = 1; i <= size; ++i) {
        POMAGMA_ASSERT_EQ(carrier.try_insert(), i);
        carrier.validate();
    }

    for (size_t i = 1; i <= size; ++i) {
        Ob dep = random_int(1, size);
        Ob rep = random_int(1, size);
        if (dep > rep) {
            carrier.merge(dep, rep);
        }
        carrier.validate();

        Ob ob = random_int(1, size);
        carrier.find(ob);
        carrier.validate();
    }

    for (size_t i = 1; i <= size; ++i) {
        if (random_bool(0.5)) {
            if (carrier.contains(i) and carrier.find(i) != i) {
                carrier.unsafe_remove(i);
            }
            carrier.validate();
        }
    }
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
