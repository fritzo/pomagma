#include "binary_relation.hpp"
#include <utility>

using namespace pomagma;

size_t g_num_moved(0);
void move_to (Ob i __attribute__((unused)), Ob j __attribute__((unused)))
{
    //std::cout << i << '-' << j << ' ' << std::flush; //DEBUG
    ++g_num_moved;
}

bool test_fun1 (Ob i, Ob j) { return i and j and i % 61u <= j % 31u; }
bool test_fun2 (Ob i, Ob j) { return i and j and i % 61u == j % 31u; }

void test_BinaryRelation (
        size_t size,
        bool (*test_fun) (Ob, Ob))
{
    POMAGMA_INFO("Testing BinaryRelation");

    POMAGMA_INFO("creating BinaryRelation of size " << size);
    Carrier carrier(size);
    const DenseSet & support = carrier.support();


    POMAGMA_INFO("testing position insertion");
    for (Ob i = 1; i <= size; ++i) {
         carrier.unsafe_insert();
    }
    size_t item_count = size;
    for (Ob i = 1; i <= size; ++i) {
        if (random_bool(0.5)) {
            carrier.unsafe_remove(i);
            --item_count;
        }
    }
    POMAGMA_ASSERT_EQ(item_count, support.count_items());

    POMAGMA_INFO("testing pair insertion");
    BinaryRelation rel(carrier, move_to);
    rel.validate();
    size_t num_pairs = 0;
    for (auto i = support.iter(); i.ok(); i.next()) {
    for (auto j = support.iter(); j.ok(); j.next()) {
        if (test_fun(*i, *j)) {
            rel.insert(*i, *j);
            ++num_pairs;
        }
    } }
    POMAGMA_INFO("  " << num_pairs << " pairs inserted");
    rel.validate();
    POMAGMA_ASSERT_EQ(num_pairs, rel.count_pairs());

    POMAGMA_INFO("testing pair containment");
    num_pairs = 0;
    for (auto i = support.iter(); i.ok(); i.next()) {
    for (auto j = support.iter(); j.ok(); j.next()) {
        if (test_fun(*i, *j)) {
            POMAGMA_ASSERT(rel.find_Lx(*i, *j),
                    "Lx relation missing " << *i << ',' << *j);
            POMAGMA_ASSERT(rel.find_Rx(*i, *j),
                    "Rx relation missing " << *i << ',' << *j);
            ++num_pairs;
        } else {
            POMAGMA_ASSERT(not rel.find_Lx(*i, *j),
                    "Lx relation has extra " << *i << ',' << *j);
            POMAGMA_ASSERT(not rel.find_Rx(*i, *j),
                    "Rx relation has extra " << *i << ',' << *j);
        }
    } }
    POMAGMA_INFO("  " << num_pairs << " pairs found");
    rel.validate();
    POMAGMA_ASSERT_EQ(num_pairs, rel.count_pairs());

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
    POMAGMA_INFO("  " << g_num_moved << " pairs moved in merging");
    rel.validate();
    POMAGMA_ASSERT_EQ(item_count, support.count_items());

    POMAGMA_INFO("testing line iterator (lhs fixed)");
    num_pairs = 0;
    size_t seen_item_count = 0;
    item_count = support.count_items();
    for (auto lhs_iter = support.iter();
        lhs_iter.ok();
        lhs_iter.next())
    {
        ++seen_item_count;
        DenseSet set = rel.get_Lx_set(*lhs_iter);
        for (auto rhs_iter = set.iter(); rhs_iter.ok(); rhs_iter.next()) {
            ++num_pairs;
        }
    }
    POMAGMA_INFO("  Iterated over " << seen_item_count << " items");
    POMAGMA_INFO("  Iterated over " << num_pairs << " pairs");
    rel.validate();
    POMAGMA_ASSERT_EQ(seen_item_count, item_count);
    size_t true_size = rel.count_pairs();
    POMAGMA_ASSERT_EQ(num_pairs, true_size);

    POMAGMA_INFO("testing line iterator (rhs fixed)");
    num_pairs = 0;
    seen_item_count = 0;
    for (auto rhs_iter = support.iter();
        rhs_iter.ok();
        rhs_iter.next())
    {
        ++seen_item_count;
        DenseSet set = rel.get_Rx_set(*rhs_iter);
        for (auto lhs_iter = set.iter(); lhs_iter.ok(); lhs_iter.next()) {
            ++num_pairs;
        }
    }
    POMAGMA_INFO("  Iterated over " << seen_item_count << " items");
    POMAGMA_INFO("  Iterated over " << num_pairs << " pairs");
    rel.validate();
    POMAGMA_ASSERT_EQ(seen_item_count, item_count);
    POMAGMA_ASSERT_EQ(num_pairs, true_size);
}

int main ()
{
    Log::title("Running Binary Relation Test");

    for (size_t i = 0; i < 4; ++i) {
        test_BinaryRelation(i + (1 << 9), test_fun1);
        test_BinaryRelation(i + (1 << 9), test_fun2);
    }

    return 0;
}
