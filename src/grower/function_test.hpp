#pragma once 

#include "carrier.hpp"

namespace pomagma
{

size_t g_insert_count = 0;
void insert_callback (Ob i)
{
    POMAGMA_DEBUG("inserting " << i);
    ++g_insert_count;
}

size_t g_merge_count = 0;
void merge_callback (Ob i)
{
    POMAGMA_DEBUG("merging " << i);
    ++g_merge_count;
}

inline void random_init (Carrier & carrier)
{
    POMAGMA_ASSERT_EQ(carrier.item_count(), 0);
    const size_t size = carrier.item_dim();
    g_insert_count = 0;
    for (Ob i = 1; i <= size; ++i) {
        POMAGMA_ASSERT(carrier.try_insert(), "insertion failed");
    }
    POMAGMA_ASSERT_EQ(g_insert_count, size);
    for (Ob i = 1; i <= size; ++i) {
        if (random_bool(0.5)) {
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

void test_merge (Carrier & carrier)
{
    POMAGMA_INFO("Checking unsafe_merge");
    const DenseSet & support = carrier.support();
    size_t merge_count = 0;
    g_merge_count = 0;
    for (auto rep_iter = support.iter(); rep_iter.ok(); rep_iter.next())
    for (auto dep_iter = support.iter(); dep_iter.ok(); dep_iter.next()) {
        Ob dep = carrier.find(*dep_iter);
        Ob rep = carrier.find(*rep_iter);
        if ((rep < dep) and random_bool(0.1)) {
            carrier.merge(dep, rep);
            ++merge_count;
            break;
        }
    }
    POMAGMA_ASSERT_EQ(merge_count, g_merge_count);
}

template<class Example>
void test_function (size_t size)
{
    Carrier carrier(size, insert_callback, merge_callback);
    random_init(carrier);
    Example example(carrier);
    remove_deps(carrier, example.fun);
    test_merge(carrier);
    remove_deps(carrier, example.fun);
}

template<class Example>
void test_function ()
{
    for (size_t exponent = 0; exponent < 10; ++exponent) {
        test_function<Example>((1 << exponent) - 1);
    }

    for (size_t i = 0; i < 4; ++i) {
        test_function<Example>(i + (1 << 9));
    }
}

} // namespace pomagma
