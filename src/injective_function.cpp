#include "injective_function.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

InjectiveFunction::InjectiveFunction (const Carrier & carrier)
    : m_carrier(carrier),
      m_support(carrier.support(), yes_copy_construct),
      m_set(support().item_dim()),
      m_inverse_set(support().item_dim()),
      m_values(pomagma::alloc_blocks<oid_t>(1 + item_dim())),
      m_inverse(pomagma::alloc_blocks<oid_t>(1 + item_dim()))
{
    POMAGMA_DEBUG("creating InjectiveFunction with " << item_dim() << " values");

    bzero(m_values, (1 + item_dim()) * sizeof(oid_t));
    bzero(m_inverse, (1 + item_dim()) * sizeof(oid_t));
}

InjectiveFunction::~InjectiveFunction ()
{
    pomagma::free_blocks(m_values);
    pomagma::free_blocks(m_inverse);
}

// for growing
void InjectiveFunction::move_from (const InjectiveFunction & other)
{
    POMAGMA_DEBUG("Copying InjectiveFunction");

    size_t min_item_dim = min(item_dim(), other.item_dim());
    size_t byte_count = sizeof(oid_t) * min_item_dim;
    memcpy(m_values, other.m_values, byte_count);
    memcpy(m_inverse, other.m_inverse, byte_count);

    m_set.move_from(other.m_set);
    m_inverse_set.move_from(other.m_inverse_set);
}

//----------------------------------------------------------------------------
// Diagnostics

void InjectiveFunction::validate () const
{
    POMAGMA_DEBUG("Validating InjectiveFunction");

    m_set.validate();
    m_inverse_set.validate();

    POMAGMA_DEBUG("validating set-values consistency");
    for (oid_t key = 1; key <= item_dim(); ++key) {
        bool bit = m_set(key);
        oid_t val = m_values[key];

        if (not m_support.contains(key)) {
            POMAGMA_ASSERT(not val, "found unsupported val at " << key);
            POMAGMA_ASSERT(not bit, "found unsupported bit at " << key);
        } else if (not val) {
            POMAGMA_ASSERT(not bit, "found supported null value at " << key);
        } else {
            POMAGMA_ASSERT(bit, "found unsupported value at " << key);
            POMAGMA_ASSERT(m_inverse[val] == m_carrier.get_rep(key),
                    "value, inverse mismatch: " <<
                    key << " -> " << val << " <- " << m_inverse[val]);
        }
    }

    for (oid_t val = 1; val <= item_dim(); ++val) {
        bool bit = m_inverse_set(val);
        oid_t key = m_inverse[val];

        if (not m_support.contains(key)) {
            POMAGMA_ASSERT(not val, "found unsupported key at " << val);
            POMAGMA_ASSERT(not bit, "found unsupported bit at " << val);
        } else if (not key) {
            POMAGMA_ASSERT(not bit, "found supported null key at " << val);
        } else {
            POMAGMA_ASSERT(bit, "found unsupported value at " << val);
            POMAGMA_ASSERT(m_values[key] == m_carrier.get_rep(val),
                    "inverse, value mismatch: " <<
                    val << " <- " << key << " -> " << m_values[key]);
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

    TODO("remove inverse")

    if (bool_ref dep_bit = m_set(dep)) {
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

    TODO("merge inverse")

    if (bool_ref dep_bit = m_set(dep)) {
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
