#include "injective_function.hpp"
#include "function_test.hpp"
#include <vector>

using namespace pomagma;

inline Ob example_fun (Ob i)
{
    const size_t big_prime = (1ul << 31ul) - 1;
    Ob result = big_prime % (i + 1);
    if (result > 1) {
        return result;
    } else {
        return 0;
    }
}

void merge_callback (Ob i)
{
    POMAGMA_DEBUG("merging " << i);
}

struct Example
{
    InjectiveFunction fun;

    Example (Carrier & carrier) : fun(carrier)
    {
        const DenseSet & support = carrier.support();

        POMAGMA_INFO("Defining function");
        InjectiveFunction fun(carrier);
        fun.validate();

        for (auto i = support.iter(); i.ok(); i.next()) {
            Ob val = example_fun(*i);
            if (val and support.contains(val)) {
                fun.insert(*i, val);
            }
        }
        fun.validate();

        POMAGMA_INFO("Checking function values");
        for (auto i = support.iter(); i.ok(); i.next()) {
            Ob val = example_fun(*i);
            if (val and support.contains(val)) {
                POMAGMA_ASSERT(fun.defined(*i), "missing value at " << *i);
                POMAGMA_ASSERT(fun.find(*i) == val, "bad value at " << *i);
            } else {
                POMAGMA_ASSERT(not fun.defined(*i),
                        "unexpected value at " << *i);
            }
        }
        fun.validate();
    }
};

int main ()
{
    Log::title("InjectiveFunction Test");
    test_function<Example>();

    return 0;
}
