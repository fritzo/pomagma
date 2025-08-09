#include "queues.hpp"

#include <pomagma/util/sort_uniq.hpp>

#include "carrier.hpp"

namespace pomagma {

void NullaryFunctionQueue::process_mergers(const Carrier& carrier) {
    std::vector<Ob> new_tasks;
    size_t new_i = 0;
    for (size_t old_i = 0, end = m_tasks.size(); old_i != end; ++old_i) {
        Ob old_task = m_tasks[old_i];
        Ob new_task = carrier.find(old_task);
        if (new_task == old_task) {
            if (new_i != old_i) m_tasks[new_i] = old_task;
            ++new_i;
        } else {
            new_tasks.emplace_back(new_task);
        }
    }
    if (new_tasks.empty()) return;
    m_tasks.resize(new_i);
    sort_uniq(new_tasks);
    union_sort_uniq(m_tasks, new_tasks);
}

void InjectiveFunctionQueue::process_mergers(const Carrier& carrier) {
    std::vector<std::pair<Ob, Ob>> new_tasks;
    size_t new_i = 0;
    for (size_t old_i = 0, end = m_tasks.size(); old_i != end; ++old_i) {
        auto& old_task = m_tasks[old_i];
        std::pair<Ob, Ob> new_task{carrier.find(old_task.first),
                                   carrier.find(old_task.second)};
        if (new_task == old_task) {
            if (new_i != old_i) m_tasks[new_i] = old_task;
            ++new_i;
        } else {
            new_tasks.emplace_back(new_task);
        }
    }
    if (new_tasks.empty()) return;
    m_tasks.resize(new_i);
    sort_uniq(new_tasks);
    union_sort_uniq(m_tasks, new_tasks);
}

void BinaryFunctionQueue::clear() {
    if (m_tasks.capacity() > 1024) {
        decltype(m_tasks)().swap(m_tasks);
    } else {
        m_tasks.clear();
    }
    m_tasks.reserve(1024);
}

void BinaryFunctionQueue::process_mergers(const Carrier& carrier) {
    std::vector<std::tuple<Ob, Ob, Ob>> new_tasks;
    size_t new_i = 0;
    for (size_t old_i = 0, end = m_tasks.size(); old_i != end; ++old_i) {
        auto& old_task = m_tasks[old_i];
        auto& [lhs, rhs, val] = old_task;
        std::tuple<Ob, Ob, Ob> new_task{carrier.find(lhs), carrier.find(rhs),
                                        carrier.find(val)};
        if (new_task == old_task) {
            if (new_i != old_i) m_tasks[new_i] = old_task;
            ++new_i;
        } else {
            new_tasks.emplace_back(new_task);
        }
    }
    if (new_tasks.empty()) return;
    m_tasks.resize(new_i);
    sort_uniq(new_tasks);
    union_sort_uniq(m_tasks, new_tasks);
}

void SymmetricFunctionQueue::clear() {
    if (m_tasks.capacity() > 1024) {
        decltype(m_tasks)().swap(m_tasks);
    } else {
        m_tasks.clear();
    }
    m_tasks.reserve(1024);
}

void SymmetricFunctionQueue::process_mergers(const Carrier& carrier) {
    std::vector<std::tuple<Ob, Ob, Ob>> new_tasks;
    size_t new_i = 0;
    for (size_t old_i = 0, end = m_tasks.size(); old_i != end; ++old_i) {
        auto& old_task = m_tasks[old_i];
        auto& [old_lhs, old_rhs, old_val] = old_task;
        Ob new_lhs = carrier.find(old_lhs);
        Ob new_rhs = carrier.find(old_rhs);
        Ob new_val = carrier.find(old_val);
        if (new_lhs > new_rhs)
            std::swap(new_lhs, new_rhs);  // sort for symmetry
        std::tuple<Ob, Ob, Ob> new_task{new_lhs, new_rhs, new_val};
        if (old_task == new_task) {
            if (new_i != old_i) m_tasks[new_i] = old_task;
            ++new_i;
        } else {
            new_tasks.emplace_back(new_task);
        }
    }
    if (new_tasks.empty()) return;
    m_tasks.resize(new_i);
    sort_uniq(new_tasks);
    union_sort_uniq(m_tasks, new_tasks);
}

void UnaryRelationQueue::process_mergers(const Carrier& carrier) {
    std::vector<Ob> new_tasks;
    size_t new_i = 0;
    for (size_t old_i = 0, end = m_tasks.size(); old_i != end; ++old_i) {
        Ob old_task = m_tasks[old_i];
        Ob new_task = carrier.find(old_task);
        if (new_task == old_task) {
            if (new_i != old_i) m_tasks[new_i] = old_task;
            ++new_i;
        } else {
            new_tasks.emplace_back(new_task);
        }
    }
    if (new_tasks.empty()) return;
    m_tasks.resize(new_i);
    sort_uniq(new_tasks);
    union_sort_uniq(m_tasks, new_tasks);
}

void BinaryRelationQueue::clear() {
    m_tasks.clear();
    m_index.clear();
}

void BinaryRelationQueue::build_index() {
    m_index.clear();
    m_index.reserve(m_tasks.size());
    for (auto& [hi, _] : m_tasks) m_index.emplace_back(hi);
    std::sort(m_index.begin(), m_index.end());
}

std::pair<BinaryRelationQueue::HighPair, const BinaryRelationQueue::LowQueue&>
BinaryRelationQueue::get_task(size_t i) const noexcept {
    HighPair hi = m_index.at(i);
    const LowQueue& lo_queue = m_tasks.find(hi)->second;
    return {hi, lo_queue};
}

void BinaryRelationQueue::process_mergers(const Carrier& carrier) {
    m_index.clear();  // index will be invalidated

    // Collect new tasks
    std::unordered_map<HighPair, LowQueue, ObPairHash> new_tasks;
    for (auto& [hi, lo_queue] : m_tasks) {
        const auto [i_hi, j_hi] = hi;

        // Process lo_queue and check if any objects changed
        size_t new_pos = 0;
        for (size_t old_pos = 0, end = lo_queue.size(); old_pos != end;
             ++old_pos) {
            const auto [i_lo, j_lo] = lo_queue[old_pos];
            Ob old_i = ob_from_hi_lo(i_hi, i_lo);
            Ob old_j = ob_from_hi_lo(j_hi, j_lo);
            Ob new_i = carrier.find(old_i);
            Ob new_j = carrier.find(old_j);

            if (new_i == old_i && new_j == old_j) {
                if (new_pos != old_pos) lo_queue[new_pos] = lo_queue[old_pos];
                ++new_pos;
            } else {
                auto [new_i_hi, new_i_lo] = ob_to_hi_lo(new_i);
                auto [new_j_hi, new_j_lo] = ob_to_hi_lo(new_j);
                HighPair new_hi = {new_i_hi, new_j_hi};
                new_tasks[new_hi].emplace_back(new_i_lo, new_j_lo);
            }
        }
        lo_queue.resize(new_pos);
    }
    if (new_tasks.empty()) return;

    // Merge new tasks into m_tasks
    for (auto& [hi, source_queue] : new_tasks) {
        sort_uniq(source_queue);
        auto& destin_queue = m_tasks[hi];
        if (destin_queue.empty()) {
            destin_queue = std::move(source_queue);
        } else {
            union_sort_uniq(destin_queue, source_queue);
        }
    }

    // Eliminate empty tiles
    for (auto it = m_tasks.begin(); it != m_tasks.end();) {
        if (it->second.empty()) {
            it = m_tasks.erase(it);
        } else {
            ++it;
        }
    }
}

}  // namespace pomagma
