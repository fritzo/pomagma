#include "util.hpp"
#include "inverse_bin_fun.hpp"
#include "binary_function.hpp"

using namespace pomagma;

void test_random (size_t size, float fill = 0.3)
{
    POMAGMA_INFO("Buiding fun,inv of size " << size);
    Carrier carrier(size);
    const dense_set & support = carrier.support();
    BinaryFunction fun(carrier);
    inverse_bin_fun inv(carrier);

    for (oid_t i = 1; i <= size; ++i) {
        if (random_bool(0.8)) {
            carrier.insert(i);
        }
    }

    POMAGMA_INFO("testing insertion");
    size_t insert_count = size * size * fill;
    for (size_t n = 0; n < insert_count; ++n) {
        oid_t lhs;
        oid_t rhs;
        while (true) {
            lhs = random_int(1, size);
            if (not support.contains(lhs)) continue;
            rhs = random_int(1, size);
            if (not support.contains(rhs)) continue;
            if (fun.contains(lhs, rhs)) continue;
            break;
        }
        oid_t val = random_int(1, size);

        fun.insert(lhs, rhs, val);
        inv.insert(lhs, rhs, val);
    }

    fun.validate();
    inv.validate(fun);
}

int main ()
{
    test_random(1 << 9);

    // TODO test with multiple threads

    return 0;
}
