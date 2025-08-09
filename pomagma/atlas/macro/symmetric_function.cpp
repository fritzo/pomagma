#include "symmetric_function.hpp"

#include <cstring>
#include <pomagma/util/aligned_alloc.hpp>
#include <pomagma/util/sort_uniq.hpp>

namespace pomagma {

thread_local std::unordered_map<const SymmetricFunction*,
                                SymmetricFunction::Queue>*
    SymmetricFunction::s_consequents = nullptr;

SymmetricFunction::SymmetricFunction(Carrier& carrier) : m_lines(carrier) {
    POMAGMA_DEBUG("creating SymmetricFunction");
}

SymmetricFunction::SymmetricFunction(Carrier& carrier,
                                     SymmetricFunction&& other)
    : m_lines(carrier, std::move(other.m_lines)),
      m_values(std::move(other.m_values)) {
    POMAGMA_DEBUG("resizing SymmetricFunction");
}

void SymmetricFunction::validate() const {
    POMAGMA_INFO("Validating SymmetricFunction");

    m_lines.validate();

    POMAGMA_DEBUG("validating line-value consistency");
    for (size_t i = 1; i <= item_dim(); ++i)
        for (size_t j = i; j <= item_dim(); ++j) {
            auto val_iter = m_values.find(assert_sorted_pair(i, j));

            if (not(support().contains(i) and support().contains(j))) {
                POMAGMA_ASSERT(val_iter == m_values.end(),
                               "found unsupported lhs, rhs: " << i << ',' << j);
            } else if (val_iter != m_values.end()) {
                POMAGMA_ASSERT(defined(i, j),
                               "found undefined value: " << i << ',' << j);
                Ob val = val_iter->second;
                POMAGMA_ASSERT(val, "found zero value: " << i << ',' << j);
                POMAGMA_ASSERT(support().contains(val),
                               "found unsupported value: " << i << ',' << j);
            } else {
                POMAGMA_ASSERT(not defined(i, j),
                               "found defined null value: " << i << ',' << j);
            }
        }
}

void SymmetricFunction::log_stats(const std::string& prefix) const {
    m_lines.log_stats(prefix);
}

void SymmetricFunction::clear() {
    m_lines.clear();
    m_values.clear();
}

void SymmetricFunction::process_mergers() {
    for (auto& pair : m_values) {
        Ob& dep = pair.second;
        Ob rep = carrier().find(dep);
        if (rep != dep) {
            dep = rep;
        }
    }

    m_consequents.process_mergers(carrier());
}

void SymmetricFunction::unsafe_merge(const Ob dep) {
    POMAGMA_ASSERT5(support().contains(dep), "unsupported dep: " << dep);
    Ob rep = carrier().find(dep);
    POMAGMA_ASSERT5(support().contains(rep), "unsupported rep: " << rep);
    POMAGMA_ASSERT4(rep != dep, "self merge: " << dep << "," << rep);

    // (dep, dep) -> (rep, rep)
    if (defined(dep, dep)) {
        auto dep_iter = m_values.find(std::make_pair(dep, dep));
        Ob dep_val = dep_iter->second;
        m_values.erase(dep_iter);
        m_lines.Lx(dep, dep).zero();
        Ob& rep_val = m_values[std::make_pair(rep, rep)];
        if (carrier().set_or_merge(rep_val, dep_val)) {
            m_lines.Lx(rep, rep).one();
        }
    }

    // (dep, rhs) --> (rep, rhs) for rhs != dep
    rep = carrier().find(rep);
    for (auto iter = iter_lhs(dep); iter.ok(); iter.next()) {
        Ob rhs = *iter;
        auto dep_iter = m_values.find(make_sorted_pair(dep, rhs));
        Ob dep_val = dep_iter->second;
        m_values.erase(dep_iter);
        m_lines.Rx(dep, rhs).zero();
        Ob& rep_val = m_values[make_sorted_pair(rep, rhs)];
        if (carrier().set_or_merge(rep_val, dep_val)) {
            m_lines.Rx(rep, rhs).one();
        }
    }
    DenseSet dep_set(item_dim(), m_lines.Lx(dep));
    DenseSet rep_set(item_dim(), m_lines.Lx(rep));
    rep_set.merge(dep_set);

    // values must be updated in batch by process_mergers
}

void SymmetricFunction::Queue::clear() {
    if (m_tasks.capacity() > 1024) {
        decltype(m_tasks)().swap(m_tasks);
    } else {
        m_tasks.clear();
    }
    m_tasks.reserve(1024);
}

void SymmetricFunction::lazy_gather() const {
    Queue& source = worker_consequents();
    if (source.m_tasks.empty()) return;
    sort_uniq(source.m_tasks);
    {
        std::unique_lock<std::mutex> lock(m_consequents_mutex);
        union_sort_uniq(m_consequents.m_tasks, source.m_tasks);
    }
    source.clear();
}

size_t SymmetricFunction::lazy_flush() const {
    if (m_consequents.m_tasks.empty()) return 0;
    for (const auto [lhs, rhs, val] : m_consequents.m_tasks) {
        insert(lhs, rhs, val);
    }
    size_t theorem_count = m_consequents.m_tasks.size();
    m_consequents.clear();
    return theorem_count;
}

void SymmetricFunction::Queue::process_mergers(const Carrier& carrier) {
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
