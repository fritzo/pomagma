#include "unary_function.hpp"
#include <vector>

using namespace pomagma;

inline oid_t example_fun (oid_t i)
{
    const size_t big_prime = (1ul << 31ul) - 1;
    return big_prime % (i + 1);
}

void test_basic (size_t size)
{
    POMAGMA_INFO("Defining function");
    dense_set support(size);
    for (oid_t i = 1; i <= size; ++i) {
        if (random_bool(0.8)) {
            support.insert(i);
        }
    }
    UnaryFunction fun(support);
    for (dense_set::iterator i(support); i.ok(); i.next()) {
        oid_t val = example_fun(*i);
        if (val > 1) {
            fun.insert(*i, val);
        }
    }
    fun.validate();

    POMAGMA_INFO("Checking function values");
    for (dense_set::iterator i(support); i.ok(); i.next()) {
        oid_t val = example_fun(*i);
        if (val > 1) {
            POMAGMA_ASSERT(fun.contains(*i), "missing value at " << *i);
            POMAGMA_ASSERT(fun.get_value(*i) == val, "bad value at " << *i);
        } else {
            POMAGMA_ASSERT(not fun.contains(*i), "unexpected value at " << *i);
        }
    }

    POMAGMA_INFO("Validating");
    fun.validate();
}

int main ()
{
    Log::title("Dense Unary Function Test");

    for (size_t i = 0; i < 4; ++i) {
        test_basic(i + (1 << 9));
    }

    for (size_t exponent = 0; exponent < 10; ++exponent) {
        test_basic(1 << exponent);
    }

    return 0;
}
