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
    const DenseSet m_support;
    DenseSet m_set;
    DenseSet m_inverse_set;
    Ob * const m_values;
    Ob * const m_inverse;

public:

    // set wrappers
    const DenseSet & get_set () const { return m_set; }
    const DenseSet & get_inverse_set () const { return m_inverse_set; }

    // ctors & dtors
    InjectiveFunction (const Carrier & carrier);
    ~InjectiveFunction ();
    void move_from (const InjectiveFunction & other); // for growing

    // function calling
private:
    Ob & value (Ob key);
    Ob & inverse (Ob val);
public:
    Ob value (Ob key) const;
    Ob inverse (Ob val) const;
    Ob get_value (Ob key) const { return value(key); }
    Ob get_inverse (Ob val) const { return inverse(val); }
    Ob operator() (Ob key) const { return value(key); }
    Ob find (Ob key) const { return value(key); }
    Ob find_inverse (Ob val) const { return inverse(val); }

    // attributes
    size_t item_dim () const { return m_set.item_dim(); }
private:
    const DenseSet & support () const { return m_support; }
public:
    size_t count_items () const { return m_set.count_items(); } // slow!
    void validate () const;

    // element operations
    // TODO add a replace method for merging
    void insert (
            Ob key,
            Ob val,
            void merge_values(Ob, Ob)); // dep, rep
    void remove (Ob key);
    bool contains (Ob key) const
    {
        POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
        return m_set.contains(key);
    }

    // support operations
    void remove (
            const Ob i,
            void remove_value(Ob)); // rem
    void merge (
            const Ob i,
            const Ob j,
            void merge_values(Ob, Ob), // dep, rep
            void move_value(Ob, Ob)); // val, key
};

inline Ob & InjectiveFunction::value (Ob key)
{
    POMAGMA_ASSERT_RANGE_(5, key, item_dim());
    return m_values[key];
}

inline Ob InjectiveFunction::value (Ob key) const
{
    POMAGMA_ASSERT_RANGE_(5, key, item_dim());
    return m_values[key];
}

inline Ob & InjectiveFunction::inverse (Ob val)
{
    POMAGMA_ASSERT_RANGE_(5, val, item_dim());
    return m_inverse[val];
}

inline Ob InjectiveFunction::inverse (Ob val) const
{
    POMAGMA_ASSERT_RANGE_(5, val, item_dim());
    return m_inverse[val];
}

inline void InjectiveFunction::insert (
        Ob key,
        Ob val,
        void merge_values(Ob, Ob)) // dep, rep
{
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);
    POMAGMA_ASSERT5(val, "tried to set val to zero at " << key);

    Ob & old_val = value(key);
    POMAGMA_ASSERT2(not old_val,
            "double insertion at " << key << ": " << old_val);
    old_val = val;

    bool_ref bit = m_set(key);
    POMAGMA_ASSERT4(not bit, "double insertion at " << key);
    bit.one();

    Ob & old_key = inverse(val);
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

inline void InjectiveFunction::remove (Ob key)
{
    POMAGMA_ASSERT5(support().contains(key), "unsupported key: " << key);

    TODO("deal with inverse removal")

    Ob & old_val = value(key);
    POMAGMA_ASSERT2(old_val, "double removal at " << key);
    old_val = 0;

    bool_ref bit = m_set(key);
    POMAGMA_ASSERT4(bit, "double removal at " << key);
    bit.zero();
}

} // namespace pomagma

#endif // POMAGMA_INJECTIVE_FUNCTION_HPP
