#include "nullary_function.hpp"

#include <cstring>
#include <pomagma/util/aligned_alloc.hpp>
#include <pomagma/util/sort_uniq.hpp>

namespace pomagma {

thread_local std::unordered_map<const NullaryFunction*, NullaryFunction::Queue>*
    NullaryFunction::s_worker_queues = nullptr;

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
    Queue& source = worker_queue();
    if (source.m_tasks.empty()) return;
    sort_uniq(source.m_tasks);
    {
        std::unique_lock<std::mutex> lock(m_queue_mutex);
        union_sort_uniq(m_queue.m_tasks, source.m_tasks);
    }
    source.clear();
}

size_t NullaryFunction::lazy_flush() const {
    if (m_queue.m_tasks.empty()) return 0;
    for (const auto val : m_queue.m_tasks) {
        insert(val);
    }
    size_t theorem_count = m_queue.m_tasks.size();
    m_queue.clear();
    return theorem_count;
}

}  // namespace pomagma
