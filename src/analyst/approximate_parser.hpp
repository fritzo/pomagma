#pragma once

#include <pomagma/analyst/approximator.hpp>
#include <pomagma/platform/parser.hpp>

namespace pomagma
{

class ApproximateReducer : noncopyable
{
public:

    typedef Approximation Term;

    explicit ApproximateReducer (Approximator & approximator)
        : m_approximator(approximator)
    {}

    Approximation reduce (
            const std::string &,
            const NullaryFunction * fun)
    {
        return m_approximator.find(* fun);
    }

    Approximation reduce (
            const std::string &,
            const InjectiveFunction * fun,
            const Approximation & key)
    {
        return m_approximator.find(* fun, key);
    }

    Approximation reduce (
            const std::string &,
            const BinaryFunction * fun,
            const Approximation & lhs,
            const Approximation & rhs)
    {
        return m_approximator.find(* fun, lhs, rhs);
    }

    Approximation reduce (
            const std::string &,
            const SymmetricFunction * fun,
            const Approximation & lhs,
            const Approximation & rhs)
    {
        return m_approximator.find(* fun, lhs, rhs);
    }

    // TODO
    //Approximation reduce (
    //        const std::string &,
    //        const BinaryRelation * rel,
    //        const Approximation & lhs,
    //        const Approximation & rhs)
    //{
    //    return m_approximator.find(* rel, lhs, rhs);
    //}

private:

    Approximator & m_approximator;
};

class ApproximateParser : public TermParser<ApproximateReducer>
{
public:

    ApproximateParser (Approximator & approximator)
        : TermParser<ApproximateReducer>(approximator.signature(), m_reducer),
          m_reducer(approximator)
    {
    }

private:

    ApproximateReducer m_reducer;
};

} // namespace pomagma
