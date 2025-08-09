#include "queues.hpp"

#include <pomagma/util/sort_uniq.hpp>

#include "carrier.hpp"

namespace pomagma {

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

}  // namespace pomagma
