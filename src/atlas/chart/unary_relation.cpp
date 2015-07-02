#include "unary_relation.hpp"

namespace pomagma
{

static void noop_callback (const UnaryRelation *, Ob) {}

UnaryRelation::UnaryRelation (
        const Carrier & carrier,
        void (*insert_callback) (const UnaryRelation *, Ob))
    : m_carrier(carrier),
      m_set(item_dim()),
      m_insert_callback(insert_callback ? insert_callback : noop_callback)
{
    POMAGMA_DEBUG("creating UnaryRelation with " << word_dim() << " words");
}

UnaryRelation::~UnaryRelation ()
{
}

void UnaryRelation::validate () const
{
    UniqueLock lock(m_mutex);

    POMAGMA_INFO("Validating UnaryRelation");

    m_set.validate();

    for (auto iter = m_set.iter(); iter.ok(); iter.next()) {
        Ob ob = *iter;
        POMAGMA_ASSERT(supports(ob), "relation is unsupported at " << ob);
    }
}

void UnaryRelation::validate_disjoint (const UnaryRelation & other) const
{
    UniqueLock lock(m_mutex);

    POMAGMA_INFO("Validating disjoint pair of UnaryRelations");

    // validate supports agree
    POMAGMA_ASSERT_EQ(support().item_dim(), other.support().item_dim());
    POMAGMA_ASSERT_EQ(
            support().count_items(),
            other.support().count_items());
    POMAGMA_ASSERT(support() == other.support(),
            "UnaryRelation supports differ");

    // validate disjointness
    POMAGMA_ASSERT(m_set.disjoint(other.m_set), "UnaryRelations intersect");
}

void UnaryRelation::log_stats (const std::string & prefix) const
{
    size_t count = count_items();
    size_t capacity = item_dim();
    float density = 1.0f * count / capacity;
    POMAGMA_INFO(prefix << " " <<
        count << " / " << capacity << " = " << density << " full");
}

void UnaryRelation::clear ()
{
    memory_barrier();
    m_set.zero();
    memory_barrier();
}

// policy: callback whenever rel(dep) but not rel(rep)
void UnaryRelation::unsafe_merge (Ob dep)
{
    UniqueLock lock(m_mutex);

    Ob rep = m_carrier.find(dep);
    POMAGMA_ASSERT4(rep < dep, "UnaryRelation tried to merge item with self");

    if (m_set(dep).fetch_zero()) {
        if (not m_set(rep).fetch_one()) {
            m_insert_callback(this, rep);
        }
    }
}

} // namespace pomagma
