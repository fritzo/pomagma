#pragma once

#include <pomagma/platform/parser.hpp>
#include <pomagma/macrostructure/structure_impl.hpp>

namespace pomagma
{

class FindParser : public OldParser
{
public:

    FindParser (Signature & signature) : OldParser(signature) {}

protected:

    Ob check_insert (const NullaryFunction * fun)
    {
        return fun->find();
    }

    Ob check_insert (const InjectiveFunction * fun, Ob key)
    {
        return fun->find(key);
    }

    Ob check_insert (const BinaryFunction * fun, Ob lhs, Ob rhs)
    {
        return fun->find(lhs, rhs);
    }

    Ob check_insert (const SymmetricFunction * fun, Ob lhs, Ob rhs)
    {
        return fun->find(lhs, rhs);
    }
};

} // namespace pomagma
