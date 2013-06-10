#pragma once

#include <pomagma/platform/parser.hpp>
#include <pomagma/microstructure/structure_impl.hpp>

namespace pomagma
{

class InsertParser : public Parser
{
public:

    InsertParser (Signature & signature)
        : Parser(signature),
          m_carrier(* signature.carrier())
    {
    }

protected:

    Ob check_insert (const NullaryFunction * fun)
    {
        Ob val = fun->find();
        if (not val) {
            val = m_carrier.try_insert();
            POMAGMA_ASSERT(val, "carrier is full");
            fun->insert(val);
        }
        return val;
    }

    Ob check_insert (const InjectiveFunction * fun, Ob key)
    {
        Ob val = fun->find(key);
        if (not val) {
            val = m_carrier.try_insert();
            POMAGMA_ASSERT(val, "carrier is full");
            fun->insert(key, val);
        }
        return val;
    }

    Ob check_insert (const BinaryFunction * fun, Ob lhs, Ob rhs)
    {
        Ob val = fun->find(lhs, rhs);
        if (not val) {
            val = m_carrier.try_insert();
            POMAGMA_ASSERT(val, "carrier is full");
            fun->insert(lhs, rhs, val);
        }
        return val;
    }

    Ob check_insert (const SymmetricFunction * fun, Ob lhs, Ob rhs)
    {
        Ob val = fun->find(lhs, rhs);
        if (not val) {
            val = m_carrier.try_insert();
            POMAGMA_ASSERT(val, "carrier is full");
            fun->insert(lhs, rhs, val);
        }
        return val;
    }

private:

    Carrier & m_carrier;
};

} // namespace pomagma
