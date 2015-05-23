#pragma once

#include <pomagma/macrostructure/util.hpp>
#include <pomagma/macrostructure/structure_impl.hpp>

namespace pomagma
{

struct Approximation
{
    Ob ob;
    DenseSet upper;
    DenseSet lower;
    DenseSet nupper;
    DenseSet nlower;

    Approximation (size_t item_dim, Ob top, Ob bot)
        : ob(0),
          upper(item_dim),
          lower(item_dim),
          nupper(item_dim),
          nlower(item_dim)
    {
        upper.insert(top);
        lower.insert(bot);
    }
    // only the ob constructor is aliased
    Approximation (
            Ob o,
            const BinaryRelation & less,
            const BinaryRelation & nless)
        : ob(o),
          upper(less.get_Lx_set(o)),
          lower(less.get_Rx_set(o)),
          nupper(nless.get_Lx_set(o)),
          nlower(nless.get_Rx_set(o))
    {
        POMAGMA_ASSERT(ob, "ob is undefined");
    }
    Approximation (
            Ob lb,
            Ob ub,
            const BinaryRelation & less,
            const BinaryRelation & nless)
        : ob(0),
          upper(less.item_dim()),
          lower(less.item_dim()),
          nupper(nless.item_dim()),
          nlower(nless.item_dim())
    {
        POMAGMA_ASSERT(lb, "lb is undefined");
        POMAGMA_ASSERT(ub, "ub is undefined");
        POMAGMA_ASSERT(less.find(lb, ub), "expected LESS lb ub");
        POMAGMA_ASSERT(not nless.find(lb, ub), "expected not NLESS lb ub");
        upper = less.get_Lx_set(ub);
        lower = less.get_Rx_set(lb);
        nupper = nless.get_Lx_set(ub);  // TODO is this right?
        nlower = nless.get_Rx_set(lb);  // TODO is this right?
    }
    Approximation (Approximation && other)
        : ob(other.ob),
          upper(std::move(other.upper)),
          lower(std::move(other.lower)),
          nupper(std::move(other.nupper)),
          nlower(std::move(other.nlower))
    {}
    Approximation (const Approximation &) = delete;

    void operator= (const Approximation & other)
    {
        ob = other.ob;
        upper = other.upper;
        lower = other.lower;
        nupper = other.nupper;
        nlower = other.nlower;
    }
    bool operator== (const Approximation & other) const
    {
        return ob == other.ob
            and upper == other.upper
            and lower == other.lower
            and nupper == other.nupper
            and nlower == other.nlower;
    }
    bool operator!= (const Approximation & other) const
    {
        return not operator==(other);
    }
};

class Approximator : noncopyable
{
public:

    explicit Approximator (Structure & structure);

    Signature & signature () { return m_structure.signature(); }

    size_t test ();
    void validate (const Approximation & approx);

    Approximation known (Ob ob) { return Approximation(ob, m_less, m_nless); }
    Approximation unknown () { return Approximation(m_item_dim, m_top, m_bot); }
    Approximation truthy () { return known(m_identity); }
    Approximation falsey () { return known(m_bot); }
    Approximation maybe ()
    {
        return Approximation(m_bot, m_identity, m_less, m_nless);
    }

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
    void map_lhs_val (
            const BinaryFunction & fun,
            const DenseSet & lhs_pos_set,
            DenseSet & rhs_neg_set,
            const DenseSet & val_neg_set,
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

} // namespace pomagma
