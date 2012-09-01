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
    const DenseSet m_support; // aliased
    Ob m_value;

public:

    NullaryFunction (const Carrier & carrier);
    void move_from (const NullaryFunction & other); // for growing

    // function calling
private:
    Ob & value () { return m_value; }
public:
    Ob value () const { return m_value; }
    Ob get_value () const { return m_value; }
    Ob find () const { return m_value; }

    // attributes
private:
    const DenseSet & support () const { return m_support; }
public:
    void validate () const;

    // element operations
    // TODO add a replace method for merging
    void insert (Ob val);
    void remove ();
    bool defined () const { return m_value; }

    // support operations
    void remove (const Ob i);
    void merge (const Ob i, const Ob j);
};

inline void NullaryFunction::insert (Ob val)
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
