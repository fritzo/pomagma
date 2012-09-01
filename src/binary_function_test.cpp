#include "binary_function.hpp"
#include <vector>

using namespace pomagma;

inline Ob example_fun (Ob i, Ob j)
{
    return ((i % j) > (j % i)) * ((i * i + j + 1) % max(i, j));
}

void test_basic (size_t size)
{
    POMAGMA_INFO("Defining function");
    Carrier carrier(size);
    const DenseSet & support = carrier.support();
    BinaryFunction fun(carrier);

    for (Ob i = 1; i <= size; ++i) {
        if (random_bool(0.8)) {
            carrier.insert(i);
        }
    }
    for (DenseSet::Iterator i(support); i.ok(); i.next()) {
    for (DenseSet::Iterator j(support); j.ok(); j.next()) {
        Ob k = example_fun(*i, *j);
        if (k > 1) {
            fun.insert(*i, *j, k);
        }
    }}
    fun.validate();

    POMAGMA_INFO("Checking function values");
    std::vector<size_t> Lx_line_size(size + 1, 0);
    std::vector<size_t> Rx_line_size(size + 1, 0);
    for (DenseSet::Iterator i(support); i.ok(); i.next()) {
    for (DenseSet::Iterator j(support); j.ok(); j.next()) {
        Ob k = example_fun(*i, *j);
        if (k > 1) {
            POMAGMA_ASSERT(fun.contains(*i, *j),
                    "missing pair " << *i << ',' << *j);
            POMAGMA_ASSERT(fun.get_value(*i, *j) == k,
                    "bad value at " << *i << ',' << *j);
            ++Lx_line_size[*i];
            ++Rx_line_size[*j];
        } else {
            POMAGMA_ASSERT(not fun.contains(*i, *j),
                    "unexpected pair " << *i << ',' << *j);
        }
    }}

    POMAGMA_INFO("Validating");
    fun.validate();
}

int main ()
{
    Log::title("Dense Binary Function Test");

    for (size_t i = 0; i < 4; ++i) {
        test_basic(i + (1 << 9));
    }

    for (size_t exponent = 0; exponent < 10; ++exponent) {
        test_basic(1 << exponent);
    }

    return 0;
}
