#pragma once

#include <pomagma/structure/parser.hpp>
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
        return key ? fun->find(key) : 0;
    }

    Ob reduce (
            const std::string &,
			const BinaryFunction * fun,
			Ob lhs,
			Ob rhs)
    {
        return lhs and rhs ? fun->find(lhs, rhs) : 0;
    }

    Ob reduce (
            const std::string &,
			const SymmetricFunction * fun,
			Ob lhs,
			Ob rhs)
    {
        return lhs and rhs ? fun->find(lhs, rhs) : 0;
    }
};

class FindParser : public TermParser<FindReducer>
{
public:

    FindParser (Signature & signature)
        : TermParser(signature, m_reducer)
    {
    }

private:

    FindReducer m_reducer;
};

} // namespace pomagma
