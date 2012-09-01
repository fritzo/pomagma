#ifndef POMAGMA_INJECTIVE_FUNCTION_HPP
#define POMAGMA_INJECTIVE_FUNCTION_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include "carrier.hpp"

namespace pomagma
{

// WARNING zero/null items are not allowed

class InjectiveFunction : noncopyable
{
    const Carrier & m_carrier;
    const dense_set m_support;
    dense_set m_set;
    dense_set m_inverse_set;
    oid_t * const m_values;
    oid_t * const m_inverse;

public:

    // set wrappers
    const dense_set & get_set () const { return m_set; }
    const dense_set & get_inverse_set () const { return m_inverse_set; }

    // ctors & dtors
    InjectiveFunction (const Carrier & carrier);
    ~InjectiveFunction ();
    void move_from (const InjectiveFunction & other); // for growing

    // function calling
private:
    oid_t & value (oid_t key);
    oid_t & inverse (oid_t val);
public:
    oid_t value (oid_t key) const;
    oid_t inverse (oid_t val) const;
    oid_t get_value (oid_t key) const { return value(key); }
    oid_t get_inverse (oid_t val) const { return inverse(val); }
    oid_t operator() (oid_t key) const { return value(key); }

    // attributes
    size_t item_dim () const { return m_set.item_dim(); }
private:
    const dense_set & support () const { return m_support; }
public:
    size_t count_items () const { return m_set.count_items(); } // slow!
    void validate () const;

    // element operations
    // TODO add a replace method for merging
    void insert (
            oid_t key,
            oid_t val,
            void merge_values(oid_t, oid_t)); // dep, rep
    void remove (oid_t key);
    bool contains (oid_t key) const
    {
        POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
        return m_set.contains(key);
    }

    // support operations
    void remove (
            const oid_t i,
            void remove_value(oid_t)); // rem
    void merge (
            const oid_t i,
            const oid_t j,
            void merge_values(oid_t, oid_t), // dep, rep
            void move_value(oid_t, oid_t)); // val, key
};

inline oid_t & InjectiveFunction::value (oid_t key)
{
    POMAGMA_ASSERT_RANGE_(5, key, item_dim());
    return m_values[key];
}

inline oid_t InjectiveFunction::value (oid_t key) const
{
    POMAGMA_ASSERT_RANGE_(5, key, item_dim());
    return m_values[key];
}

inline oid_t & InjectiveFunction::inverse (oid_t val)
{
    POMAGMA_ASSERT_RANGE_(5, val, item_dim());
    return m_inverse[val];
}

inline oid_t InjectiveFunction::inverse (oid_t val) const
{
    POMAGMA_ASSERT_RANGE_(5, val, item_dim());
    return m_inverse[val];
}

inline void InjectiveFunction::insert (
        oid_t key,
        oid_t val,
        void merge_values(oid_t, oid_t)) // dep, rep
{
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    POMAGMA_ASSERT5(val, "tried to set val to zero at " << key);

    oid_t & old_val = value(key);
    POMAGMA_ASSERT2(not old_val,
            "double insertion at " << key << ": " << old_val);
    old_val = val;

    bool_ref bit = m_set(key);
    POMAGMA_ASSERT4(not bit, "double insertion at " << key);
    bit.one();

    oid_t & old_key = inverse(val);
    if (old_key) {
        if (old_key < key) {
            merge_values(key, old_key);
        } else if (old_key > key) {
            merge_values(old_key, key);
            old_key = key;
        }
    } else {
        bool_ref bit = m_inverse_set(val);
        POMAGMA_ASSERT4(not bit, "double inverse insertion at " << val);
        bit.one();

        old_key = key;
    }
}

inline void InjectiveFunction::remove (oid_t key)
{
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);

    TODO("deal with inverse removal")

    oid_t & old_val = value(key);
    POMAGMA_ASSERT2(old_val, "double removal at " << key);
    old_val = 0;

    bool_ref bit = m_set(key);
    POMAGMA_ASSERT4(bit, "double removal at " << key);
    bit.zero();
}

} // namespace pomagma

#endif // POMAGMA_INJECTIVE_FUNCTION_HPP
