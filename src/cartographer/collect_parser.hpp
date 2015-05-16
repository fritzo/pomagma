#pragma once

#include <pomagma/platform/parser.hpp>
#include <pomagma/macrostructure/structure_impl.hpp>

namespace pomagma
{

class CollectReducer : noncopyable
{
public:

    typedef Ob Term;

    CollectReducer (DenseSet & set, size_t capacity)
        : m_set(set),
          m_size(set.count_items()),
          m_capacity(capacity)
    {
        POMAGMA_ASSERT_LE(m_size, m_capacity);
    }

    Ob reduce (
            const std::string &,
            const NullaryFunction * fun)
    {
        return check_insert(fun->find());
    }

    Ob reduce (
            const std::string &,
            const InjectiveFunction * fun,
            Ob key)
    {
        return check_insert(fun->find(key));
    }

    Ob reduce (
            const std::string &,
            const BinaryFunction * fun,
            Ob lhs,
            Ob rhs)
    {
        return check_insert(fun->find(lhs, rhs));
    }

    Ob reduce (
            const std::string &,
            const SymmetricFunction * fun,
            Ob lhs,
            Ob rhs)
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

class CollectParser : public TermParser<CollectReducer>
{
public:

    CollectParser (Signature & signature, DenseSet & set, size_t capacity)
        : TermParser<CollectReducer>(signature, m_reducer),
          m_reducer(set, capacity)
    {
    }

private:

    CollectReducer m_reducer;
};

} // namespace pomagma
