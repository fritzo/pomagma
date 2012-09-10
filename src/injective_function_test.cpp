#include "injective_function.hpp"
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

Carrier * g_carrier = nullptr;

void merge_callback (Ob i)
{
    POMAGMA_DEBUG("merging " << i);
}

void test_basic (size_t size)
{
    POMAGMA_INFO("Defining function");
    Carrier carrier(size, merge_callback);
    g_carrier = & carrier;
    const DenseSet & support = carrier.support();
    for (Ob i = 1; i <= size; ++i) {
        carrier.unsafe_insert();
    }
    for (Ob i = 1; i <= size; ++i) {
        if (random_bool(0.2)) {
            carrier.unsafe_remove(i);
        }
    }

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
            POMAGMA_ASSERT(not fun.defined(*i), "unexpected value at " << *i);
        }
    }
    fun.validate();

    POMAGMA_INFO("Checking unsafe_merge");
    for (auto dep = support.iter(); dep.ok(); dep.next()) {
        for (auto rep = support.iter(); rep.ok(); rep.next()) {
            if ((*rep < *dep) and random_bool(0.25)) {
                carrier.merge(*dep, *rep);
                break;
            }
        }
    }
    bool merged;
    do {
        merged = false;
        for (auto iter = support.iter(); iter.ok(); iter.next()) {
            Ob dep = *iter;
            if (carrier.find(dep) != dep) {
                fun.unsafe_merge(dep);
                carrier.unsafe_remove(dep);
                merged = true;
            }
        }
    } while (merged);
    fun.validate();

    POMAGMA_INFO("Checking unsafe_remove");
    for (auto iter = support.iter(); iter.ok(); iter.next()) {
        if (random_bool(0.5)) {
            Ob dep = *iter;
            fun.unsafe_remove(dep);
            carrier.unsafe_remove(dep);
        }
    }
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
