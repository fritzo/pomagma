#include "symmetric_function.hpp"
#include <vector>

using namespace pomagma;

Ob gcd (Ob n, Ob m) { return m ? gcd(m, n % m) : n; }

void test_basic (Ob size)
{
    POMAGMA_INFO("Defining function");
    Carrier carrier(size);
    const DenseSet & support = carrier.support();
    for (Ob i = 1; i <= size; ++i) {
        carrier.unsafe_insert();
    }
    for (Ob i = 1; i <= size; ++i) {
        if (random_bool(0.2)) {
            carrier.unsafe_remove(i);
        }
    }

    SymmetricFunction fun(carrier);
    fun.validate();

    for (DenseSet::Iterator i(support); i.ok(); i.next())
    for (DenseSet::Iterator j(support); j.ok() and *j <= *i; j.next()) {
        Ob k = gcd(*i, *j);
        if ((k > 1) and carrier.contains(k)) {
            fun.insert(*i, *j, k);
        }
    }
    fun.validate();

    POMAGMA_INFO("Checking function values");
    std::vector<size_t> line_size(1 + size, 0);
    for (DenseSet::Iterator i(support); i.ok(); i.next())
    for (DenseSet::Iterator j(support); j.ok(); j.next()) {
        Ob k = gcd(*i, *j);
        if ((k > 1) and carrier.contains(k)) {
            POMAGMA_ASSERT(fun.defined(*i, *j),
                    "missing pair " << *i << ',' << *j);
            POMAGMA_ASSERT(fun.find(*i, *j) == k,
                    "bad value at " << *i << ',' << *j);
            ++line_size[*i];
        } else {
            POMAGMA_ASSERT(not fun.defined(*i, *j),
                    "unexpected pair " << *i << ',' << *j);
        }
    }
    fun.validate();


    POMAGMA_INFO("Checking unsafe_merge");
    for (DenseSet::Iterator dep(support); dep.ok(); dep.next()) {
        for (DenseSet::Iterator rep(support); rep.ok(); rep.next()) {
            if ((*rep < *dep) and random_bool(0.25)) {
                carrier.merge(*dep, *rep);
                break;
            }
        }
    }
    bool merged;
    do {
        merged = false;
        for (DenseSet::Iterator iter(support); iter.ok(); iter.next()) {
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
    for (DenseSet::Iterator iter(support); iter.ok(); iter.next()) {
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
    Log::title("SymmetricFunction Test");

    for (size_t i = 1; i < 4; ++i) {
        test_basic(i + (1 << 9));
    }

    for (size_t exponent = 0; exponent < 10; ++exponent) {
        test_basic(1 << exponent);
    }

    return 0;
}
