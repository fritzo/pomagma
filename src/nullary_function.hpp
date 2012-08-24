#ifndef POMAGMA_NULLARY_FUNCTION_HPP
#define POMAGMA_NULLARY_FUNCTION_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include "carrier.hpp"

namespace pomagma
{

// WARNING zero/null items are not allowed

class NullaryFunction : noncopyable
{
    const Carrier & m_carrier;
    const dense_set m_support; // aliased
    oid_t m_value;

public:

    NullaryFunction (const Carrier & carrier);
    void move_from (const NullaryFunction & other); // for growing

    // function calling
private:
    oid_t & value () { return m_value; }
public:
    oid_t value () const { return m_value; }
    oid_t get_value () const { return m_value; }

    // attributes
private:
    const dense_set & support () const { return m_support; }
public:
    void validate () const;

    // element operations
    // TODO add a replace method for merging
    void insert (oid_t val);
    void remove ();
    bool defined () const { return m_value; }

    // support operations
    void remove (const oid_t i);
    void merge (const oid_t i, const oid_t j);
};

inline void NullaryFunction::insert (oid_t val)
{
    POMAGMA_ASSERT5(val, "tried to set value to zero");
    POMAGMA_ASSERT5(support().contains(val), "unsupported value: " << val);

    POMAGMA_ASSERT2(not m_value, "double insertion");
    m_value = val;
}

inline void NullaryFunction::remove ()
{
    POMAGMA_ASSERT2(m_value, "double removal");
    m_value = 0;
}

} // namespace pomagma

#endif // POMAGMA_NULLARY_FUNCTION_HPP
