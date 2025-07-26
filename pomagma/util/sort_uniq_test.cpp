#include <pomagma/util/sort_uniq.hpp>
#include <pomagma/util/util.hpp>
#include <string>
#include <vector>

using namespace pomagma;

rng_t rng;

void test_sort_uniq_basic() {
    POMAGMA_INFO("Testing sort_uniq basic functionality");

    // Test with integers
    {
        std::vector<int> v = {3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5};
        std::vector<int> expected = {1, 2, 3, 4, 5, 6, 9};
        sort_uniq(v);
        POMAGMA_ASSERT(v == expected, "sort_uniq failed for integers");
    }

    // Test with strings
    {
        std::vector<std::string> v = {"apple", "banana", "apple", "cherry",
                                      "banana"};
        std::vector<std::string> expected = {"apple", "banana", "cherry"};
        sort_uniq(v);
        POMAGMA_ASSERT(v == expected, "sort_uniq failed for strings");
    }

    // Test empty vector
    {
        std::vector<int> v;
        sort_uniq(v);
        POMAGMA_ASSERT(v.empty(), "sort_uniq failed for empty vector");
    }

    // Test single element
    {
        std::vector<int> v = {42};
        std::vector<int> expected = {42};
        sort_uniq(v);
        POMAGMA_ASSERT(v == expected, "sort_uniq failed for single element");
    }

    // Test all duplicates
    {
        std::vector<int> v = {7, 7, 7, 7, 7};
        std::vector<int> expected = {7};
        sort_uniq(v);
        POMAGMA_ASSERT(v == expected, "sort_uniq failed for all duplicates");
    }

    // Test already sorted unique
    {
        std::vector<int> v = {1, 2, 3, 4, 5};
        std::vector<int> expected = {1, 2, 3, 4, 5};
        sort_uniq(v);
        POMAGMA_ASSERT(v == expected,
                       "sort_uniq failed for already sorted unique");
    }

    // Test reverse sorted with duplicates
    {
        std::vector<int> v = {5, 5, 4, 3, 3, 2, 1, 1};
        std::vector<int> expected = {1, 2, 3, 4, 5};
        sort_uniq(v);
        POMAGMA_ASSERT(v == expected,
                       "sort_uniq failed for reverse sorted with duplicates");
    }
}

void test_union_sort_uniq_basic() {
    POMAGMA_INFO("Testing union_sort_uniq basic functionality");

    // Test basic union
    {
        std::vector<int> destin = {1, 3, 5, 7};
        std::vector<int> source = {2, 4, 6, 8};
        std::vector<int> expected = {1, 2, 3, 4, 5, 6, 7, 8};
        union_sort_uniq(destin, source);
        POMAGMA_ASSERT(destin == expected,
                       "union_sort_uniq failed for disjoint sorted vectors");
    }

    // Test with overlapping elements
    {
        std::vector<int> destin = {1, 3, 5, 7, 9};
        std::vector<int> source = {2, 3, 4, 7, 8};
        std::vector<int> expected = {1, 2, 3, 4, 5, 7, 8, 9};
        union_sort_uniq(destin, source);
        POMAGMA_ASSERT(destin == expected,
                       "union_sort_uniq failed for overlapping vectors");
    }

    // Test empty source
    {
        std::vector<int> destin = {1, 2, 3};
        std::vector<int> source;
        std::vector<int> expected = {1, 2, 3};
        union_sort_uniq(destin, source);
        POMAGMA_ASSERT(destin == expected,
                       "union_sort_uniq failed for empty source");
    }

    // Test empty destination
    {
        std::vector<int> destin;
        std::vector<int> source = {1, 2, 3};
        std::vector<int> expected = {1, 2, 3};
        union_sort_uniq(destin, source);
        POMAGMA_ASSERT(destin == expected,
                       "union_sort_uniq failed for empty destination");
    }

    // Test both empty
    {
        std::vector<int> destin;
        std::vector<int> source;
        union_sort_uniq(destin, source);
        POMAGMA_ASSERT(destin.empty(), "union_sort_uniq failed for both empty");
    }

    // Test identical vectors
    {
        std::vector<int> destin = {1, 2, 3};
        std::vector<int> source = {1, 2, 3};
        std::vector<int> expected = {1, 2, 3};
        union_sort_uniq(destin, source);
        POMAGMA_ASSERT(destin == expected,
                       "union_sort_uniq failed for identical vectors");
    }

    // Test source completely contained in destination
    {
        std::vector<int> destin = {1, 2, 3, 4, 5};
        std::vector<int> source = {2, 4};
        std::vector<int> expected = {1, 2, 3, 4, 5};
        union_sort_uniq(destin, source);
        POMAGMA_ASSERT(
            destin == expected,
            "union_sort_uniq failed when source is subset of destination");
    }

    // Test destination completely contained in source
    {
        std::vector<int> destin = {2, 4};
        std::vector<int> source = {1, 2, 3, 4, 5};
        std::vector<int> expected = {1, 2, 3, 4, 5};
        union_sort_uniq(destin, source);
        POMAGMA_ASSERT(
            destin == expected,
            "union_sort_uniq failed when destination is subset of source");
    }
}

void test_sort_uniq_random(size_t size, rng_t& rng) {
    POMAGMA_INFO("Testing sort_uniq with random data of size " << size);

    std::uniform_int_distribution<int> dist(1, size / 2 + 1);
    std::vector<int> v;
    std::vector<int> reference;

    // Generate random data with potential duplicates
    for (size_t i = 0; i < size; ++i) {
        int val = dist(rng);
        v.push_back(val);
        reference.push_back(val);
    }

    // Apply sort_uniq
    sort_uniq(v);

    // Verify result is sorted
    for (size_t i = 1; i < v.size(); ++i) {
        POMAGMA_ASSERT(v[i - 1] < v[i], "Result is not sorted");
    }

    // Verify no duplicates
    for (size_t i = 1; i < v.size(); ++i) {
        POMAGMA_ASSERT(v[i - 1] != v[i], "Result contains duplicates");
    }

    // Verify all unique elements from original are present
    std::sort(reference.begin(), reference.end());
    auto last = std::unique(reference.begin(), reference.end());
    reference.resize(std::distance(reference.begin(), last));

    POMAGMA_ASSERT(v == reference,
                   "sort_uniq result doesn't match expected unique elements");
}

void test_union_sort_uniq_random(size_t size, rng_t& rng) {
    POMAGMA_INFO("Testing union_sort_uniq with random data of size " << size);

    std::uniform_int_distribution<int> dist(1, size + 1);

    // Generate two random sorted vectors
    std::vector<int> destin, source;
    for (size_t i = 0; i < size / 2; ++i) {
        destin.push_back(dist(rng));
        source.push_back(dist(rng));
    }

    sort_uniq(destin);
    sort_uniq(source);

    // Create expected result
    std::vector<int> expected = destin;
    expected.insert(expected.end(), source.begin(), source.end());
    sort_uniq(expected);

    // Test union_sort_uniq
    union_sort_uniq(destin, source);

    POMAGMA_ASSERT(destin == expected, "union_sort_uniq random test failed");

    // Verify result is sorted
    for (size_t i = 1; i < destin.size(); ++i) {
        POMAGMA_ASSERT(destin[i - 1] < destin[i],
                       "union_sort_uniq result is not sorted");
    }
}

void test_performance(size_t size) {
    POMAGMA_INFO("Testing performance with size " << size);

    std::uniform_int_distribution<int> dist(1, size / 10 + 1);
    std::vector<int> v;

    // Generate data with many duplicates
    for (size_t i = 0; i < size; ++i) {
        v.push_back(dist(rng));
    }

    size_t original_size = v.size();
    sort_uniq(v);
    size_t final_size = v.size();

    POMAGMA_INFO("Reduced from " << original_size << " to " << final_size
                                 << " elements");
    POMAGMA_ASSERT(final_size <= original_size,
                   "Final size should not exceed original size");
}

int main() {
    Log::Context log_context("Sort Uniq Test");

    test_sort_uniq_basic();
    test_union_sort_uniq_basic();

    // Test with various sizes
    const std::vector<size_t> sizes = {0, 1, 2, 5, 10, 50, 100, 1000};

    for (size_t size : sizes) {
        if (size > 0) {
            test_sort_uniq_random(size, rng);
            test_union_sort_uniq_random(size, rng);
        }
    }

    // Performance tests
    for (size_t exp = 1; exp <= 16; ++exp) {
        test_performance(1 << exp);
    }

    return 0;
}