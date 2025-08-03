#include "unary_relation.hpp"

#include <pomagma/util/sort_uniq.hpp>
namespace pomagma {

thread_local std::unordered_map<const UnaryRelation*, UnaryRelation::Queue>*
    UnaryRelation::s_consequents = nullptr;

UnaryRelation::UnaryRelation(const Carrier& carrier)
    : m_carrier(carrier), m_set(item_dim()) {
    POMAGMA_DEBUG("creating UnaryRelation with " << word_dim() << " words");
}

UnaryRelation::UnaryRelation(const Carrier& carrier, UnaryRelation&& other)
    : m_carrier(carrier), m_set(item_dim()) {
    POMAGMA_DEBUG("resizing UnaryRelation with " << word_dim() << " words");

    for (auto iter = other.iter(); iter.ok(); iter.next()) {
        Ob ob = *iter;
        POMAGMA_ASSERT_LE(ob, item_dim());
        m_set.raw_insert(ob);
    }
}

UnaryRelation::~UnaryRelation() {}

void UnaryRelation::validate() const {
    POMAGMA_INFO("Validating UnaryRelation");

    m_set.validate();

    for (auto iter = m_set.iter(); iter.ok(); iter.next()) {
        Ob ob = *iter;
        POMAGMA_ASSERT(supports(ob), "relation is unsupported at " << ob);
    }
}

void UnaryRelation::validate_disjoint(const UnaryRelation& other) const {
    POMAGMA_INFO("Validating disjoint pair of UnaryRelations");

    // validate supports agree
    POMAGMA_ASSERT_EQ(support().item_dim(), other.support().item_dim());
    POMAGMA_ASSERT_EQ(support().count_items(), other.support().count_items());
    POMAGMA_ASSERT(support() == other.support(),
                   "UnaryRelation supports differ");

    // validate disjointness
    POMAGMA_ASSERT(m_set.disjoint(other.m_set), "UnaryRelations intersect");
}

void UnaryRelation::log_stats(const std::string& prefix) const {
    size_t count = count_items();
    size_t capacity = item_dim();
    float density = 1.0f * count / capacity;
    POMAGMA_INFO(prefix << " " << count << " / " << capacity << " = " << density
                        << " full");
}

void UnaryRelation::unsafe_merge(Ob dep) {
    Ob rep = m_carrier.find(dep);
    POMAGMA_ASSERT4(rep < dep, "UnaryRelation tried to merge item with self");

    if (m_set(dep).fetch_zero()) {
        m_set(rep).one();
    }
}

void UnaryRelation::lazy_gather() const {
    Queue& source = worker_consequents();
    if (source.m_tasks.empty()) return;
    sort_uniq(source.m_tasks);
    {
        std::unique_lock<std::mutex> lock(m_consequents_mutex);
        union_sort_uniq(m_consequents.m_tasks, source.m_tasks);
    }
    source.clear();
}

size_t UnaryRelation::lazy_flush() {
    if (m_consequents.m_tasks.empty()) return 0;
    for (const auto i : m_consequents.m_tasks) {
        insert(i);
    }
    size_t theorem_count = m_consequents.m_tasks.size();
    m_consequents.clear();
    return theorem_count;
}

}  // namespace pomagma
