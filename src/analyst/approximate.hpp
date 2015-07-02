#pragma once

#include <pomagma/atlas/world/util.hpp>
#include <pomagma/atlas/world/structure_impl.hpp>
#include <pomagma/atlas/parser.hpp>

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
    // only the ob constructor is aliased
    Approximation (Ob o, const BinaryRelation & less)
        : ob(o),
          upper(less.get_Lx_set(o)),
          lower(less.get_Rx_set(o))
    {
        POMAGMA_ASSERT(ob, "ob is undefined");
    }
    Approximation (Ob lb, Ob ub, const BinaryRelation & less)
        : ob(0),
          upper(less.item_dim()),
          lower(less.item_dim())
    {
        POMAGMA_ASSERT(lb, "lb is undefined");
        POMAGMA_ASSERT(ub, "ub is undefined");
        POMAGMA_ASSERT(less.find(lb, ub), "expected LESS lb ub");
        upper = less.get_Lx_set(ub);
        lower = less.get_Rx_set(lb);
    }
    Approximation (Approximation && other)
        : ob(other.ob),
          upper(std::move(other.upper)),
          lower(std::move(other.lower))
    {}
    Approximation (const Approximation &) = delete;

    void operator= (const Approximation & other)
    {
        ob = other.ob;
        upper = other.upper;
        lower = other.lower;
    }
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

    Approximator (Structure & structure);

    Signature & signature () { return m_structure.signature(); }

    size_t test ();
    void validate (const Approximation & approx);

    Approximation known (Ob ob) { return Approximation(ob, m_less); }
    Approximation unknown () { return Approximation(m_item_dim, m_top, m_bot); }
    Approximation truthy () { return known(m_identity); }
    Approximation falsey () { return known(m_bot); }
    Approximation maybe () { return Approximation(m_bot, m_identity, m_less); }

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
    Approximation find (
            const UnaryRelation & pos,
            const UnaryRelation & neg,
            const Approximation & arg);
    Approximation find (
            const BinaryRelation & pos,
            const BinaryRelation & neg,
            const Approximation & lhs,
            const Approximation & rhs);

    Approximation find (
            const std::string & name);
    Approximation find (
            const std::string & name,
            const Approximation & arg0);
    Approximation find (
            const std::string & name,
            const Approximation & arg0,
            const Approximation & arg1);

    enum Trool {
        MAYBE = 0,
        FALSE = 1,
        TRUE = 2
    };
    Trool is_top (const Approximation & approx);
    Trool is_bot (const Approximation & approx);

    struct Validity
    {
        Trool is_top;
        Trool is_bot;

        Validity () {}
        Validity (Trool t, Trool b) : is_top(t), is_bot(b) {}
        static Validity unknown () { return Validity(MAYBE, MAYBE); }
    };
    Validity is_valid (const Approximation & approx)
    {
        return Validity(is_top(approx), is_bot(approx));
    }

private:

    // returns true if closed
    bool try_close (
            Approximation & approx,
            DenseSet & temp_set);
    void close (
            Approximation & approx,
            DenseSet & temp_set);

    size_t test_less ();
    template<class Function>
    size_t test_function (
            const std::string & name,
            const Function & fun);

    void map (
            const InjectiveFunction & fun,
            const DenseSet & key_set,
            DenseSet & val_set,
            DenseSet & temp_set);
    void map (
            const BinaryFunction & fun,
            const DenseSet & lhs_set,
            const DenseSet & rhs_set,
            DenseSet & val_set,
            DenseSet & temp_set);
    void map (
            const SymmetricFunction & fun,
            const DenseSet & lhs_set,
            const DenseSet & rhs_set,
            DenseSet & val_set,
            DenseSet & temp_set);

    Structure & m_structure;
    const size_t m_item_dim;
    const Ob m_top;
    const Ob m_bot;
    const Ob m_identity;
    const BinaryRelation & m_less;
    const BinaryRelation & m_nless;
    const SymmetricFunction * const m_join;
    const SymmetricFunction * const m_rand;
    const InjectiveFunction * const m_quote;
};


class ApproximateReducer : noncopyable
{
public:

    typedef Approximation Term;

    ApproximateReducer (Approximator & approximator)
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
