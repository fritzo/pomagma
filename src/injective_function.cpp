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
      m_values(alloc_blocks<std::atomic<Ob>>(1 + item_dim())),
      m_inverse(alloc_blocks<std::atomic<Ob>>(1 + item_dim()))
{
    POMAGMA_DEBUG("creating InjectiveFunction with "
            << item_dim() << " values");

    construct_blocks(m_values, 1 + item_dim(), 0);
    construct_blocks(m_inverse, 1 + item_dim(), 0);
}

InjectiveFunction::~InjectiveFunction ()
{
    destroy_blocks(m_values, 1 + item_dim());
    free_blocks(m_values);
    destroy_blocks(m_inverse, 1 + item_dim());
    free_blocks(m_inverse);
}

void InjectiveFunction::move_from (const InjectiveFunction & other)
{
    POMAGMA_DEBUG("Copying InjectiveFunction");

    size_t min_item_dim = min(item_dim(), other.item_dim());
    size_t byte_count = sizeof(Ob) * min_item_dim;
    memcpy(m_values, other.m_values, byte_count);
    memcpy(m_inverse, other.m_inverse, byte_count);

    m_set.move_from(other.m_set);
    m_inverse_set.move_from(other.m_inverse_set);
}

void InjectiveFunction::validate () const
{
    SharedLock lock(m_mutex);

    POMAGMA_DEBUG("Validating InjectiveFunction");

    m_set.validate();
    m_inverse_set.validate();

    POMAGMA_DEBUG("validating set-values consistency");
    for (Ob key = 1; key <= item_dim(); ++key) {
        bool bit = m_set(key);
        Ob val = m_values[key];

        if (not m_support.contains(key)) {
            POMAGMA_ASSERT(not val, "found unsupported val at " << key);
            POMAGMA_ASSERT(not bit, "found unsupported bit at " << key);
        } else if (not val) {
            POMAGMA_ASSERT(not bit, "found supported null value at " << key);
        } else {
            POMAGMA_ASSERT(bit, "found unsupported value at " << key);
            POMAGMA_ASSERT(m_carrier.equal(m_inverse[val], key),
                    "value, inverse mismatch: " <<
                    key << " -> " << val << " <- " << m_inverse[val]);
        }
    }

    for (Ob val = 1; val <= item_dim(); ++val) {
        bool bit = m_inverse_set(val);
        Ob key = m_inverse[val];

        if (not m_support.contains(val)) {
            POMAGMA_ASSERT(not key, "found unsupported key at " << val);
            POMAGMA_ASSERT(not bit, "found unsupported bit at " << val);
        } else if (not key) {
            POMAGMA_ASSERT(not bit, "found supported null key at " << val);
        } else {
            POMAGMA_ASSERT(bit, "found unsupported value at " << val);
            POMAGMA_ASSERT(m_carrier.equal(m_values[key], val),
                    "inverse, value mismatch: " <<
                    val << " <- " << key << " -> " << m_values[key]);
        }
    }
}

void InjectiveFunction::remove (Ob ob)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT_RANGE_(4, ob, item_dim());

    TODO("merge occurrences as values")

    if (bool_ref bit = m_set(ob)) {
        bit.zero();
        m_values[ob] = 0;
    }

    if (bool_ref bit = m_inverse_set(ob)) {
        bit.zero();
        m_inverse[ob] = 0;
    }
}

void InjectiveFunction::merge (Ob dep, Ob rep)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT4(rep != dep, "self merge: " << dep << "," << rep);
    POMAGMA_ASSERT_RANGE_(4, dep, item_dim());
    POMAGMA_ASSERT_RANGE_(4, rep, item_dim());

    TODO("merge occurrences as values")

    if (bool_ref dep_bit = m_set(dep)) {
        dep_bit.zero();
        m_set(rep).one();

        std::atomic<Ob> & dep_val = m_values[dep];
        std::atomic<Ob> & rep_val = m_values[rep];
        m_carrier.set_and_merge(dep_val, rep_val);
        dep_val = 0;
    }

    if (bool_ref dep_bit = m_inverse_set(dep)) {
        dep_bit.zero();
        m_inverse_set(rep).one();

        std::atomic<Ob> & dep_val = m_inverse[dep];
        std::atomic<Ob> & rep_val = m_inverse[rep];
        m_carrier.set_and_merge(dep_val, rep_val);
        dep_val = 0;
    }
}

} // namespace pomagma
