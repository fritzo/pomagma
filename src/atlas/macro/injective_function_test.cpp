#include "injective_function.hpp"
#include "function_test.hpp"
#include <vector>

using namespace pomagma;

rng_t rng;

inline Ob example_fun(Ob i) {
    const size_t big_prime = (1ul << 31ul) - 1;
    Ob result = big_prime % (i + 1);
    if (result > 1) {
        return result;
    } else {
        return 0;
    }
}

struct Example {
    InjectiveFunction fun;

    explicit Example(Carrier& carrier) : fun(carrier) {
        const DenseSet& support = carrier.support();

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
                POMAGMA_ASSERT(not fun.defined(*i), "unexpected value at "
                                                        << *i);
            }
        }
        fun.validate();

        fun.clear();
        fun.validate();
        POMAGMA_ASSERT_EQ(fun.count_items(), 0);
    }
};

int main() {
    Log::Context log_context("InjectiveFunction Test");
    test_function<Example>(rng);

    return 0;
}
