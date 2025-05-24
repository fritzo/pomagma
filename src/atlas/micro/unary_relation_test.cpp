#include "unary_relation.hpp"

#include <utility>

using namespace pomagma;

rng_t rng;

size_t g_num_moved(0);
void move_to(const UnaryRelation *, Ob i __attribute__((unused))) {
    // std::cout << i << ' ' << std::flush; //DEBUG
    ++g_num_moved;
}

bool test_fun1(Ob i) { return i and i % 3u; }
bool test_fun2(Ob i) { return i and i % 61u; }

void test_UnaryRelation(size_t size, bool (*test_fun)(Ob)) {
    POMAGMA_INFO("Testing UnaryRelation");

    POMAGMA_INFO("creating UnaryRelation of size " << size);
    Carrier carrier(size);
    const DenseSet &support = carrier.support();

    POMAGMA_INFO("testing position insertion");
    for (Ob i = 1; i <= size; ++i) {
        POMAGMA_ASSERT(carrier.try_insert(), "insertion failed");
    }
    size_t item_count = size;
    std::bernoulli_distribution randomly_remove(0.5);
    for (Ob i = 1; i <= size; ++i) {
        if (randomly_remove(rng)) {
            carrier.unsafe_remove(i);
            --item_count;
        }
    }
    POMAGMA_ASSERT_EQ(item_count, support.count_items());

    POMAGMA_INFO("testing pair insertion");
    UnaryRelation rel(carrier, move_to);
    rel.validate();
    size_t num_items = 0;
    for (auto i = support.iter(); i.ok(); i.next()) {
        if (test_fun(*i)) {
            rel.insert(*i);
            ++num_items;
        }
    }
    POMAGMA_INFO("  " << num_items << " items inserted");
    rel.validate();
    POMAGMA_ASSERT_EQ(num_items, rel.count_items());

    POMAGMA_INFO("testing pair containment");
    num_items = 0;
    for (auto i = support.iter(); i.ok(); i.next()) {
        if (test_fun(*i)) {
            POMAGMA_ASSERT(rel.find(*i), "relation missing " << *i);
            ++num_items;
        } else {
            POMAGMA_ASSERT(not rel.find(*i), "relation has extra " << *i);
        }
    }
    POMAGMA_INFO("  " << num_items << " items found");
    rel.validate();
    POMAGMA_ASSERT_EQ(num_items, rel.count_items());

    POMAGMA_INFO("testing position merging");
    for (Ob i = 1; i <= size / 3; ++i) {
        if (i % 3) continue;
        Ob m = (2 * i) % size;
        Ob n = (2 * (size - i - 1) + 1) % size;
        if (m == n) continue;
        if (not support.contains(m)) continue;
        if (not support.contains(n)) continue;
        if (m < n) std::swap(m, n);
        carrier.merge(m, n);
        rel.unsafe_merge(m);
        carrier.unsafe_remove(m);
        --item_count;
    }
    POMAGMA_INFO("  " << g_num_moved << " items moved in merging");
    rel.validate();
    POMAGMA_ASSERT_EQ(item_count, support.count_items());

    POMAGMA_INFO("testing clear");
    rel.clear();
    rel.validate();
    POMAGMA_ASSERT_EQ(rel.count_items(), 0);
}

int main() {
    Log::Context log_context("Running Unary Relation Test");

    for (size_t i = 0; i < 4; ++i) {
        test_UnaryRelation(i + (1 << 12), test_fun1);
        test_UnaryRelation(i + (1 << 12), test_fun2);
    }

    return 0;
}
