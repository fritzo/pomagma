#pragma once 

#include "carrier.hpp"

namespace pomagma
{

size_t g_merge_count = 0;
void merge_callback (Ob i)
{
    POMAGMA_DEBUG("merging " << i);
    ++g_merge_count;
}

inline void random_init (Carrier & carrier, rng_t & rng)
{
    POMAGMA_ASSERT_EQ(carrier.item_count(), 0);
    const size_t size = carrier.item_dim();
    for (Ob i = 1; i <= size; ++i) {
        POMAGMA_ASSERT(carrier.insert(), "insertion failed");
    }
    POMAGMA_ASSERT_EQ(carrier.item_count(), size);
    std::bernoulli_distribution randomly_remove(0.5);
    for (Ob i = 1; i <= size; ++i) {
        if (randomly_remove(rng)) {
            carrier.unsafe_remove(i);
        }
    }
}

template<class Function>
void remove_deps (Carrier & carrier, Function & fun)
{
    POMAGMA_INFO("Merging deps");
    const DenseSet & support = carrier.support();
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
    POMAGMA_ASSERT_EQ(carrier.rep_count(), carrier.item_count());
    fun.validate();
}

void test_merge (Carrier & carrier, rng_t & rng)
{
    POMAGMA_INFO("Checking unsafe_merge");
    const DenseSet & support = carrier.support();
    size_t merge_count = 0;
    g_merge_count = 0;
    std::bernoulli_distribution randomly_merge(0.1);
    for (auto rep_iter = support.iter(); rep_iter.ok(); rep_iter.next())
    for (auto dep_iter = support.iter(); dep_iter.ok(); dep_iter.next()) {
        Ob dep = carrier.find(*dep_iter);
        Ob rep = carrier.find(*rep_iter);
        if ((rep < dep) and randomly_merge(rng)) {
            carrier.merge(dep, rep);
            ++merge_count;
            break;
        }
    }
    POMAGMA_ASSERT_EQ(merge_count, g_merge_count);
}

template<class Example>
void test_function (size_t size, rng_t & rng)
{
    Carrier carrier(size, merge_callback);
    random_init(carrier, rng);
    Example example(carrier);
    remove_deps(carrier, example.fun);
    test_merge(carrier, rng);
    remove_deps(carrier, example.fun);
}

template<class Example>
void test_function (rng_t & rng)
{
    for (size_t exponent = 0; exponent < 10; ++exponent) {
        test_function<Example>((1 << exponent) - 1, rng);
    }

    for (size_t i = 0; i < 4; ++i) {
        test_function<Example>(i + (1 << 9), rng);
    }
}

} // namespace pomagma
