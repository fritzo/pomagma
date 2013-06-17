#pragma once

#include <pomagma/platform/parser.hpp>
#include <pomagma/macrostructure/structure_impl.hpp>

namespace pomagma
{

class CollectParser : public OldParser
{
public:

    CollectParser (Signature & signature, DenseSet & set, size_t capacity)
        : OldParser(signature),
          m_set(set),
          m_size(set.count_items()),
          m_capacity(capacity)
    {
        POMAGMA_ASSERT_LE(m_size, m_capacity);
    }

protected:

    Ob check_insert (const NullaryFunction * fun)
    {
        return check_insert(fun->find());
    }

    Ob check_insert (const InjectiveFunction * fun, Ob key)
    {
        return check_insert(fun->find(key));
    }

    Ob check_insert (const BinaryFunction * fun, Ob lhs, Ob rhs)
    {
        return check_insert(fun->find(lhs, rhs));
    }

    Ob check_insert (const SymmetricFunction * fun, Ob lhs, Ob rhs)
    {
        return check_insert(fun->find(lhs, rhs));
    }

private:

    Ob check_insert (Ob val)
    {
        if (val) {
            bool_ref contained = m_set(val);
            if (unlikely(not contained.load())) {
                POMAGMA_ASSERT_LT(m_size, m_capacity);
                contained.one();
                m_size += 1;
            }
        }
        return val;
    }

    DenseSet & m_set;
    size_t m_size;
    const size_t m_capacity;

};

} // namespace pomagma
