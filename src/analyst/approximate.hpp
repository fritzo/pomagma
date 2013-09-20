#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure_impl.hpp>
#include <pomagma/platform/parser.hpp>

namespace pomagma
{

struct Approximation
{
    Ob ob;
    DenseSet upper;
    DenseSet lower;

    Approximation (size_t item_dim, Ob top, Ob bot)
        : ob(0),
          upper(item_dim),
          lower(item_dim)
    {
        upper.insert(top);
        lower.insert(bot);
    }
    Approximation (Ob o, const BinaryRelation & less)
        : ob(o),
          upper(less.get_Lx_set(o)),
          lower(less.get_Rx_set(o))
    {
        POMAGMA_ASSERT(ob, "ob is undefined");
    }
    Approximation (Approximation && other)
        : ob(other.ob),
          upper(std::move(other.upper)),
          lower(std::move(other.lower))
    {}
    Approximation (const Approximation &) = delete;

    bool operator== (const Approximation & other) const
    {
        return ob == other.ob
            and upper == other.upper
            and lower == other.lower;
    }
    bool operator!= (const Approximation & other) const
    {
        return not operator==(other);
    }
};

class Approximator : noncopyable
{
public:

    Approximator (Structure & structure)
        : m_structure(structure),
          m_item_dim(structure.carrier().item_dim()),
          m_top(structure.nullary_function("TOP").find()),
          m_bot(structure.nullary_function("BOT").find()),
          m_less(structure.binary_relation("LESS")),
          m_nless(structure.binary_relation("NLESS")),
          m_join(structure.signature().symmetric_function("JOIN")),
          m_rand(structure.signature().symmetric_function("RAND"))
    {
        POMAGMA_ASSERT(m_top, "TOP is not defined");
        POMAGMA_ASSERT(m_bot, "BOT is not defined");
    }

    size_t validate ();
    void validate (const Approximation & approx);

    Approximation find (
            const NullaryFunction & fun);
    Approximation find (
            const InjectiveFunction & fun,
            const Approximation & key);
    Approximation find (
            const BinaryFunction & fun,
            const Approximation & lhs,
            const Approximation & rhs);
    Approximation find (
            const SymmetricFunction & fun,
            const Approximation & lhs,
            const Approximation & rhs);

    enum Trool { FALSE, MAYBE, TRUE };
    Trool is_top (const Approximation & approx);
    Trool is_bot (const Approximation & approx);

private:

    void close (Approximation & approx);
    bool try_close (Approximation & approx);  // returns true if closed

    size_t validate_less ();
    template<class Function>
    size_t validate_function (
            const std::string & name,
            const Function & fun);

    Structure & m_structure;
    const size_t m_item_dim;
    const Ob m_top;
    const Ob m_bot;
    const BinaryRelation & m_less;
    const BinaryRelation & m_nless;
    const SymmetricFunction * const m_join;
    const SymmetricFunction * const m_rand;
};


class ApproximateReducer : noncopyable
{
public:

    typedef Approximation Term;

    ApproximateReducer (Structure & structure)
        : m_approximator(structure)
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

private:

    Approximator m_approximator;
};

class ApproximateParser : public Parser<ApproximateReducer>
{
public:

    ApproximateParser (
            Structure & structure)
        : Parser<ApproximateReducer>(structure.signature(), m_reducer),
          m_reducer(structure)
    {
    }

private:

    ApproximateReducer m_reducer;
};

} // namespace pomagma
