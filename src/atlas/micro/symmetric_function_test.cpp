#include "symmetric_function.hpp"
#include "function_test.hpp"
#include <vector>

using namespace pomagma;

rng_t rng;

inline Ob gcd (Ob n, Ob m) { return m ? gcd(m, n % m) : n; }

struct Example
{
    SymmetricFunction fun;

    Example (Carrier & carrier) : fun(carrier)
    {
        const DenseSet & support = carrier.support();

        POMAGMA_INFO("Defining function");
        for (auto i = support.iter(); i.ok(); i.next())
        for (auto j = support.iter(); j.ok() and *j <= *i; j.next()) {
            Ob k = gcd(*i, *j);
            if ((k > 1) and carrier.contains(k)) {
                fun.insert(*i, *j, k);
            }
        }
        fun.validate();

        POMAGMA_INFO("Checking function values");
        for (auto i = support.iter(); i.ok(); i.next())
        for (auto j = support.iter(); j.ok(); j.next()) {
            Ob k = gcd(*i, *j);
            if ((k > 1) and carrier.contains(k)) {
                POMAGMA_ASSERT(fun.defined(*i, *j),
                        "missing pair " << *i << ',' << *j);
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

int main ()
{
    Log::Context log_context("SymmetricFunction Test");
    test_function<Example>(rng);

    return 0;
}
