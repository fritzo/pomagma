#include "injective_function.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

InjectiveFunction::InjectiveFunction (const Carrier & carrier)
    : m_carrier(carrier),
      m_support(carrier.support(), yes_copy_construct),
      m_set(support().item_dim()),
      m_values(pomagma::alloc_blocks<oid_t>(1 + item_dim()))
{
    POMAGMA_DEBUG("creating InjectiveFunction with " << item_dim() << " values");

    bzero(m_values, (1 + item_dim()) * sizeof(oid_t));
}

InjectiveFunction::~InjectiveFunction ()
{
    pomagma::free_blocks(m_values);
}

// for growing
void InjectiveFunction::move_from (const InjectiveFunction & other)
{
    POMAGMA_DEBUG("Copying InjectiveFunction");

    size_t min_item_dim = min(item_dim(), other.item_dim());
    oid_t * destin = m_values;
    const oid_t * source = other.m_values;
    memcpy(destin, source, sizeof(oid_t) * min_item_dim);

    m_set.move_from(other.m_set);
}

//----------------------------------------------------------------------------
// Diagnostics

void InjectiveFunction::validate () const
{
    POMAGMA_DEBUG("Validating InjectiveFunction");

    m_set.validate();

    POMAGMA_DEBUG("validating set-values consistency");
    for (oid_t key = 1; key <= item_dim(); ++key) {
        bool bit = m_set(key);
        oid_t val = m_values[key];

        if (not support().contains(key)) {
            POMAGMA_ASSERT(not val, "found unsupported val at " << key);
            POMAGMA_ASSERT(not bit, "found unsupported bit at " << key);
        } else if (val) {
            POMAGMA_ASSERT(bit, "found unsupported value at " << key);
        } else {
            POMAGMA_ASSERT(not bit, "found supported null value at " << key);
        }
    }
}

//----------------------------------------------------------------------------
// Operations

void InjectiveFunction::remove(
        const oid_t dep,
        void remove_value(oid_t)) // rem
{
    POMAGMA_ASSERT_RANGE_(4, dep, item_dim());

    bool_ref dep_bit = m_set(dep);
    if (dep_bit) {
        oid_t & dep_val = value(dep);
        remove_value(dep_val);
        dep_bit.zero();
        dep_val = 0;
    }
}

void InjectiveFunction::merge(
        const oid_t dep,
        const oid_t rep,
        void merge_values(oid_t, oid_t), // dep, rep
        void move_value(oid_t, oid_t)) // val, key
{
    POMAGMA_ASSERT4(rep != dep, "self merge: " << dep << "," << rep);
    POMAGMA_ASSERT_RANGE_(4, dep, item_dim());
    POMAGMA_ASSERT_RANGE_(4, rep, item_dim());

    bool_ref dep_bit = m_set(dep);
    if (dep_bit) {
        bool_ref rep_bit = m_set(rep);
        oid_t & dep_val = value(dep);
        oid_t & rep_val = value(rep);
        if (rep_val) {
            merge_values(dep_val, rep_val);
        } else {
            move_value(dep_val, rep);
            rep_val = dep_val;
            rep_bit.one();
        }
        dep_bit.zero();
        dep_val = 0;
    }
}

} // namespace pomagma
