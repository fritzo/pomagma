#pragma once

#include <algorithm>
#include <vector>

namespace pomagma {

// Sorts and deduplicates a vector in place.
// Complexity: O(n log n) where n = x.size().
template <typename T>
void sort_uniq(std::vector<T>& x) noexcept {
    std::sort(x.begin(), x.end());
    auto last = std::unique(x.begin(), x.end());
    x.resize(std::distance(x.begin(), last));
}

// Unions source into destin in place.
// Assumes destin and source are sorted.
// Result will be sorted and deduplicated.
// Complexity: O(m + n) where m = destin.size() and n = source.size().
template <typename T>
void union_sort_uniq(std::vector<T>& destin, const std::vector<T>& source) {
    if (source.empty()) return;
    if (destin.empty()) {
        destin = source;
        return;
    }
    destin.insert(destin.end(), source.begin(), source.end());
    std::inplace_merge(destin.begin(), destin.end() - source.size(),
                       destin.end());
    auto last = std::unique(destin.begin(), destin.end());
    destin.resize(std::distance(destin.begin(), last));
}

}  // namespace pomagma