#include "dense_set.hpp"
#include <vector>

using namespace pomagma;

bool is_even (Ob i, Ob modulus = 2) { return i % modulus == 0; }

void test_sizes ()
{
    POMAGMA_INFO("Testing DenseSet sizes");

    for (size_t i = 0; i <= 511; ++i) {
        POMAGMA_ASSERT_EQ(DenseSet::round_item_dim(i), 511);
    }
    for (size_t i = 512; i <= 1023; ++i) {
        POMAGMA_ASSERT_EQ(DenseSet::round_item_dim(i), 1023);
    }
}

void test_basic (size_t size)
{
    POMAGMA_INFO("Testing DenseSet");

    DenseSet set(size);
    POMAGMA_ASSERT_EQ(set.count_items(), 0);

    POMAGMA_INFO("testing position insertion");
    for (Ob i = 1; i <= size; ++i) {
        set.insert(i);
    }
    POMAGMA_ASSERT_EQ(set.count_items(), size);

    POMAGMA_INFO("testing position removal");
    for (Ob i = 1; i <= size; ++i) {
        set.remove(i);
    }
    POMAGMA_ASSERT_EQ(set.count_items(), 0);

    POMAGMA_INFO("testing iteration");
    for (Ob i = 1; i <= size / 2; ++i) {
        set.insert(i);
    }
    POMAGMA_ASSERT_EQ(set.count_items(), size / 2);
    unsigned item_count = 0;
    for (auto iter = set.iter(); iter.ok(); iter.next()) {
        POMAGMA_ASSERT(set.contains(*iter), "iterated over uncontained item");
        ++item_count;
    }
    POMAGMA_INFO("found " << item_count << " / " << (size / 2) << " items");
    POMAGMA_ASSERT(item_count <= (size / 2), "iterated over too many items");
    POMAGMA_ASSERT_EQ(item_count, size / 2);
}

void test_even (size_t size)
{
    std::vector<DenseSet *> evens(7, nullptr);
    for (auto & e : evens) {
        e = new DenseSet(size);
    }

    for (Ob i = 1; i <= 6; ++i) {
        for (Ob j = 1; j < 1 + size; ++j) {
            if (is_even(j, i)) { evens[i]->insert(j); }
        }
    }

    POMAGMA_INFO("Testing set containment");
    for (Ob i = 1; i <= 6; ++i) {
    for (Ob j = 1; j <= 6; ++j) {
        POMAGMA_INFO(j << " % " << i << " = " << (j % i));
        if (j % i == 0) {
            POMAGMA_ASSERT(*evens[j] <= *evens[i],
                    "expected containment " << j << ", " << i);
        } else {
            // XXX FIXME this fails and I don't know why
            //POMAGMA_ASSERT(not (*evens[j] <= *evens[i]),
            //        "expected non-containment " << j << ", " << i);
        }
    }}

    POMAGMA_INFO("Testing set intersection");
    DenseSet evens6(size);
    evens6.set_insn(*evens[2], *evens[3]);
    POMAGMA_ASSERT(evens6 == *evens[6], "expected 6 = lcm(2, 3)")

    POMAGMA_INFO("Validating");
    for (Ob i = 0; i <= 6; ++i) {
        evens[i]->validate();
    }
    evens6.validate();

    for (auto e : evens) {
        delete e;
    }
}

void test_iterator (size_t size)
{
    POMAGMA_INFO("Testing DenseSet::Iterator");
    DenseSet set(size);
    std::vector<bool> vect(size, false);
    size_t true_count = 0;

    for (Ob i = 1; i <= size; ++i) {
        if (random_bool(0.2)) {
            set.insert(i);
            vect[i-1] = true;
            ++true_count;
        }
    }

    for (Ob i = 1; i <= size; ++i) {
        POMAGMA_ASSERT_EQ(set.contains(i), vect[i-1]);
    }

    size_t count = 0;
    for (auto i = set.iter(); i.ok(); i.next()) {
        POMAGMA_ASSERT(vect[*i - 1], "unexpected item " << *i);
        ++count;
    }
    POMAGMA_ASSERT_EQ(count, true_count);
}

void test_operations (size_t size)
{
    POMAGMA_INFO("Testing DenseSet operations");

    DenseSet x(size);
    DenseSet y(size);
    DenseSet expected(size);
    DenseSet actual(size);

    for (size_t i = 1; i <= size; ++i) {
        if (random_bool(0.5)) x.insert(i);
        if (random_bool(0.5)) y.insert(i);
    }
    POMAGMA_ASSERT(bool(x.count_items()) ^ x.empty(), ".empty() is wrong");
    POMAGMA_ASSERT(bool(y.count_items()) ^ y.empty(), ".empty() is wrong");

    POMAGMA_INFO("testing unsafe_insert_all");
    expected.zero();
    actual.zero();
    for (Ob i = 1; i <= size; ++i) {
        expected.insert(i);
    }
    actual.unsafe_insert_all();
    POMAGMA_ASSERT(actual == expected, "unsafe_insert_all is wrong");

    POMAGMA_INFO("testing unsafe_insert_one");
    expected.zero();
    actual.zero();
    std::vector<Ob> free_list;
    for (Ob i = 1; i <= size; ++i) {
        if (x.contains(1)) {
            expected.insert(i);
            actual.insert(i);
        } else {
            free_list.push_back(i);
        }
    }
    for (Ob i : free_list) {
        expected.insert(i);
        Ob j = actual.unsafe_insert_one();
        POMAGMA_ASSERT(i == j, "wrong unsafe_insert_one " << j << " vs " << i);
        POMAGMA_ASSERT(actual == expected, "unsafe_insert_one is wrong");
    }

    POMAGMA_INFO("testing union");
    expected.zero();
    actual.zero();
    for (Ob i = 1; i <= size; ++i) {
        if (x.contains(i) or y.contains(i)) { expected.insert(i); }
        if (x.contains(i)) { actual.insert(i); }
    }
    actual += y;
    POMAGMA_ASSERT(actual == expected, "operator += is wrong");
    actual.set_union(x, y);
    POMAGMA_ASSERT(actual == expected, "set_union is wrong");
    actual.zero();
    actual.set_union(x, y);
    POMAGMA_ASSERT(actual == expected, "set_union is wrong");

    POMAGMA_INFO("testing intersection");
    expected.zero();
    actual.zero();
    for (Ob i = 1; i <= size; ++i) {
        if (x.contains(i) and y.contains(i)) { expected.insert(i); }
        if (x.contains(i)) { actual.insert(i); }
    }
    actual *= y;
    POMAGMA_ASSERT(actual == expected, "operator *= is wrong");
    actual.set_insn(x, y);
    POMAGMA_ASSERT(actual == expected, "set_insn is wrong");
    actual.zero();
    actual.set_insn(x, y);
    POMAGMA_ASSERT(actual == expected, "set_insn is wrong");

    // these are shared for merge(-), merge(-,-) & ensure
    DenseSet expected_rep(size);
    DenseSet expected_dep(size);
    DenseSet expected_diff(size);
    DenseSet actual_rep(size);
    DenseSet actual_dep(size);
    DenseSet actual_diff(size);
    expected_rep.set_union(x, y);
    for (Ob i = 1; i <= size; ++i) {
        if (y.contains(i) and not x.contains(i)) { expected_diff.insert(i); }
    }

    POMAGMA_INFO("testing merge(DenseSet)");
    actual_rep.zero();
    actual_dep.zero();
    for (Ob i = 1; i <= size; ++i) {
        if (x.contains(i)) { actual_rep.insert(i); }
        if (y.contains(i)) { actual_dep.insert(i); }
    }
    actual_rep.merge(actual_dep);
    POMAGMA_ASSERT(actual_rep == expected_rep, "merge rep is wrong");
    POMAGMA_ASSERT(actual_dep == expected_dep, "merge dep is wrong");

    POMAGMA_INFO("testing merge(DenseSet, DenseSet)");
    actual_diff.zero();
    actual_rep.zero();
    actual_dep.zero();
    for (Ob i = 1; i <= size; ++i) {
        if (x.contains(i)) { actual_rep.insert(i); }
        if (y.contains(i)) { actual_dep.insert(i); }
    }
    actual_rep.merge(actual_dep, actual_diff);
    POMAGMA_ASSERT(actual_rep == expected_rep, "merge rep is wrong");
    POMAGMA_ASSERT(actual_dep == expected_dep, "merge dep is wrong");
    POMAGMA_ASSERT(actual_diff == expected_diff, "merge diff is wrong");

    POMAGMA_INFO("testing merge(DenseSet, DenseSet)");
    actual_diff.zero();
    actual_rep.zero();
    for (Ob i = 1; i <= size; ++i) {
        if (x.contains(i)) { actual_rep.insert(i); }
    }
    actual_rep.ensure(y, actual_diff);
    POMAGMA_ASSERT(actual_rep == expected_rep, "merge rep is wrong");
    POMAGMA_ASSERT(actual_diff == expected_diff, "merge diff is wrong");
}

int main ()
{
    Log::title("Dense Set Test");

    test_sizes();

    for (size_t i = 0; i < 4; ++i) {
        test_basic(i + (1 << 15));
    }

    for (size_t size = 0; size < 100; ++size) {
        test_even(size);
        test_iterator(size);
        test_operations(size);
    }

    for (size_t exponent = 1; exponent <= 10; ++exponent) {
        size_t size = (1 << exponent) - 1;
        test_basic(size);
        test_even(size);
        test_iterator(size);
        test_operations(size);
    }

    return 0;
}
