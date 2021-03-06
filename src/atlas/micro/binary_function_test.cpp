#include "binary_function.hpp"
#include "function_test.hpp"
#include <vector>

using namespace pomagma;

rng_t rng;

inline Ob example_fun(Ob i, Ob j) {
    return ((i % j) > (j % i)) * ((i * i + j + 1) % max(i, j));
}

struct Example {
    BinaryFunction fun;

    explicit Example(Carrier& carrier) : fun(carrier) {
        const DenseSet& support = carrier.support();

        POMAGMA_INFO("Defining function");
        fun.validate();

        for (auto i = support.iter(); i.ok(); i.next())
            for (auto j = support.iter(); j.ok(); j.next()) {
                Ob k = example_fun(*i, *j);
                if ((k > 1) and carrier.contains(k)) {
                    fun.insert(*i, *j, k);
                }
            }
        fun.validate();

        POMAGMA_INFO("Checking function values");
        for (auto i = support.iter(); i.ok(); i.next())
            for (auto j = support.iter(); j.ok(); j.next()) {
                Ob k = example_fun(*i, *j);
                if ((k > 1) and carrier.contains(k)) {
                    POMAGMA_ASSERT(fun.defined(*i, *j), "missing pair "
                                                            << *i << ',' << *j);
                    POMAGMA_ASSERT(fun.find(*i, *j) == k,
                                   "bad value at " << *i << ',' << *j);
                } else {
                    POMAGMA_ASSERT(not fun.defined(*i, *j),
                                   "unexpected pair " << *i << ',' << *j);
                }
            }
        fun.validate();

        fun.clear();
        fun.validate();
        POMAGMA_ASSERT_EQ(fun.count_pairs(), 0);
    }
};

int main() {
    Log::Context log_context("BinaryFunction Test");
    test_function<Example>(rng);

    return 0;
}
