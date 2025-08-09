#pragma once

#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

#include "pomagma/atlas/obs.hpp"

namespace pomagma {

class Carrier;

struct NullaryFunctionQueue {
    std::vector<Ob> m_tasks;
    void insert(Ob val) { m_tasks.push_back(val); }
    void clear() { std::vector<Ob>().swap(m_tasks); }
    void process_mergers(const Carrier& carrier);
};

struct InjectiveFunctionQueue {
    std::vector<std::pair<Ob, Ob>> m_tasks;
    void insert(Ob key, Ob val) { m_tasks.emplace_back(key, val); }
    void clear() { std::vector<std::pair<Ob, Ob>>().swap(m_tasks); }
    void process_mergers(const Carrier& carrier);
};

struct BinaryFunctionQueue {
    BinaryFunctionQueue() { clear(); }
    std::vector<std::tuple<Ob, Ob, Ob>> m_tasks;
    void insert(Ob lhs, Ob rhs, Ob val) { m_tasks.emplace_back(lhs, rhs, val); }
    void clear();
    void process_mergers(const Carrier& carrier);
};

struct SymmetricFunctionQueue {
    SymmetricFunctionQueue() { clear(); }
    std::vector<std::tuple<Ob, Ob, Ob>> m_tasks;

    void insert(Ob lhs, Ob rhs, Ob val) {
        if (lhs > rhs) std::swap(lhs, rhs);  // sort for symmetry
        m_tasks.emplace_back(lhs, rhs, val);
    }

    void clear();
    void process_mergers(const Carrier& carrier);
};

struct UnaryRelationQueue {
    std::vector<Ob> m_tasks;
    void insert(Ob i) { m_tasks.push_back(i); }
    void clear() { std::vector<Ob>().swap(m_tasks); }
    void process_mergers(const Carrier& carrier);
};

struct BinaryRelationQueue {
    using HighPair = std::pair<ObHigh, ObHigh>;
    using LowQueue = std::vector<std::pair<ObLow, ObLow>>;
    std::unordered_map<HighPair, LowQueue, ObPairHash> m_tasks;
    std::vector<HighPair> m_index;

    void insert(Ob i, Ob j) noexcept {
        auto [i_hi, i_lo] = ob_to_hi_lo(i);
        auto [j_hi, j_lo] = ob_to_hi_lo(j);
        m_tasks[{i_hi, j_hi}].emplace_back(i_lo, j_lo);
    }

    void clear();
    void process_mergers(const Carrier& carrier);

    // methods for processing tiles of (i,j) pairs
    void build_index();
    size_t task_count() const { return m_tasks.size(); }
    std::pair<HighPair, const LowQueue&> get_task(size_t i) const noexcept;
};

}  // namespace pomagma
