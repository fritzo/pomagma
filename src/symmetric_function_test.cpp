#include "symmetric_function.hpp"
#include <vector>

using namespace pomagma;

Ob gcd (Ob n, Ob m) { return m ? gcd(m, n % m) : n; }

void test_basic (Ob size)
{
    POMAGMA_INFO("Defining function");
    Carrier carrier(size);
    const DenseSet & support = carrier.support();
    SymmetricFunction fun(carrier);

    for (Ob i = 1; i <= size; ++i) {
        carrier.unsafe_insert();
    }
    for (Ob i = 1; i <= size; ++i) {
        if (random_bool(0.2)) {
            carrier.unsafe_remove(i);
        }
    }
    for (DenseSet::Iterator i(support); i.ok(); i.next()) {
    for (DenseSet::Iterator j(support); j.ok() and *j <= *i; j.next()) {
        Ob k = gcd(*i, *j);
        if (k > 1) {
            fun.insert(*i, *j, k);
        }
    }}
    fun.validate();

    POMAGMA_INFO("Checking function values");
    std::vector<size_t> line_size(1 + size, 0);
    for (DenseSet::Iterator i(support); i.ok(); i.next()) {
    for (DenseSet::Iterator j(support); j.ok(); j.next()) {
        Ob k = gcd(*i, *j);
        if (k > 1) {
            POMAGMA_ASSERT(fun.defined(*i, *j),
                    "function does not contain good pair " << *i << ',' << *j);
            POMAGMA_ASSERT(fun.find(*i, *j) == k,
                    "bad value at " << *i << ',' << *j);
            ++line_size[*i];
        } else {
            POMAGMA_ASSERT(not fun.defined(*i, *j),
                    "function contains bad pair " << *i << ',' << *j);
        }
    }}

    POMAGMA_INFO("Validating");
    fun.validate();
}

int main ()
{
    Log::title("Dense Symmetric Function Test");

    for (size_t i = 0; i < 4; ++i) {
        test_basic(i + (1 << 9));
    }

    for (size_t exponent = 0; exponent < 10; ++exponent) {
        test_basic(1 << exponent);
    }

    return 0;
}
