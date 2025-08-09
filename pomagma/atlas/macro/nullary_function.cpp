#include "nullary_function.hpp"

#include <cstring>
#include <pomagma/util/aligned_alloc.hpp>
#include <pomagma/util/sort_uniq.hpp>

namespace pomagma {

thread_local std::unordered_map<const NullaryFunction*, NullaryFunction::Queue>*
    NullaryFunction::s_consequents = nullptr;

NullaryFunction::NullaryFunction(const Carrier& carrier)
    : m_carrier(carrier), m_value(0) {
    POMAGMA_DEBUG("creating NullaryFunction");
}

NullaryFunction::NullaryFunction(const Carrier& carrier,
                                 NullaryFunction&& other)
    : m_carrier(carrier), m_value(other.m_value) {
    POMAGMA_DEBUG("resizing NullaryFunction");
    POMAGMA_ASSERT(m_value <= m_carrier.item_dim(),
                   "value not supported by carrier");
}

void NullaryFunction::validate() const {
    POMAGMA_INFO("Validating NullaryFunction");

    Ob value = m_value;
    if (value) {
        POMAGMA_ASSERT(support().contains(value),
                       "unsupported value: " << value);
    }
}

void NullaryFunction::log_stats(const std::string& prefix) const {
    if (not m_value) {
        POMAGMA_INFO(prefix << " undefined");
    }
}

void NullaryFunction::unsafe_merge(Ob dep) {
    Ob rep = m_carrier.find(dep);
    POMAGMA_ASSERT4(rep < dep, "bad merge: " << dep << "," << rep);
    POMAGMA_ASSERT_RANGE_(4, dep, support().item_dim());
    POMAGMA_ASSERT_RANGE_(4, rep, support().item_dim());

    if (m_value == dep) {
        m_value = rep;
    }
}

void NullaryFunction::lazy_gather() const {
    Queue& source = worker_consequents();
    if (source.m_tasks.empty()) return;
    sort_uniq(source.m_tasks);
    {
        std::unique_lock<std::mutex> lock(m_consequents_mutex);
        union_sort_uniq(m_consequents.m_tasks, source.m_tasks);
    }
    source.clear();
}

size_t NullaryFunction::lazy_flush() const {
    if (m_consequents.m_tasks.empty()) return 0;
    for (const auto val : m_consequents.m_tasks) {
        insert(val);
    }
    size_t theorem_count = m_consequents.m_tasks.size();
    m_consequents.clear();
    return theorem_count;
}

void NullaryFunction::Queue::process_mergers(const Carrier& carrier) {
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

}  // namespace pomagma
