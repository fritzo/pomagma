#pragma once

#include <pomagma/platform/parser.hpp>
#include <pomagma/macrostructure/structure_impl.hpp>

namespace pomagma
{

class FindReducer : noncopyable
{
public:

    typedef Ob Term;

    Ob reduce (
            const std::string &,
			const NullaryFunction * fun)
    {
        return fun->find();
    }

    Ob reduce (
            const std::string &,
			const InjectiveFunction * fun,
			Ob key)
    {
        return fun->find(key);
    }

    Ob reduce (
            const std::string &,
			const BinaryFunction * fun,
			Ob lhs,
			Ob rhs)
    {
        return fun->find(lhs, rhs);
    }

    Ob reduce (
            const std::string &,
			const SymmetricFunction * fun,
			Ob lhs,
			Ob rhs)
    {
        return fun->find(lhs, rhs);
    }
};

class FindParser : public Parser<FindReducer>
{
public:

    FindParser (Signature & signature)
        : Parser(signature, m_reducer)
    {
    }

private:

    FindReducer m_reducer;
};

} // namespace pomagma
