#include "approximate.hpp"
#include <vector>

namespace pomagma
{

namespace
{

inline void map (
        const InjectiveFunction & fun,
        const DenseSet & key_set,
        DenseSet & val_set)
{
    POMAGMA_ASSERT_EQ(key_set.item_dim(), val_set.item_dim());

    for (auto iter = fun.defined().iter_insn(key_set); iter.ok(); iter.next()) {
        Ob key = * iter;
        Ob val = fun.find(key);
        val_set.insert(val);
    }
}

template<class Function>
inline void map (
        const Function & fun,
        const DenseSet & lhs_set,
        const DenseSet & rhs_set,
        DenseSet & val_set)
{
    POMAGMA_ASSERT_EQ(lhs_set.item_dim(), val_set.item_dim());
    POMAGMA_ASSERT_EQ(rhs_set.item_dim(), val_set.item_dim());

    for (auto iter = lhs_set.iter(); iter.ok(); iter.next()) {
        Ob lhs = * iter;
        for (auto iter = rhs_set.iter_insn(fun.get_Lx_set(lhs));
            iter.ok(); iter.next())
        {
            Ob rhs = * iter;
            Ob val = fun.find(lhs, rhs);
            val_set.insert(val);
        }
    }
}

} // anonymoous namespace


void Approximator::validate (const Approximation & approx)
{
    POMAGMA_ASSERT_EQ(approx.lower.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(approx.upper.item_dim(), m_item_dim);

    std::vector<Ob> set;
    for (auto iter = approx.lower.iter_insn(approx.upper);
        iter.ok(); iter.next())
    {
        set.push_back(* iter);
    }
    for (auto x : set) {
        for (auto y : set) {
            POMAGMA_ASSERT(not m_nless.find(x, y),
                "approximation contains distinct obs: " << x << ", " << y);
        }
    }

    Approximation closed(m_item_dim, m_top, m_bot);
    closed = approx;
    close(closed);
    POMAGMA_ASSERT_EQ(closed.ob, approx.ob);
    POMAGMA_ASSERT(closed.upper == approx.upper, "upper set is not closed");
    POMAGMA_ASSERT(closed.lower == approx.lower, "lower set is not closed");
}

void Approximator::close (Approximation & approx)
{
    for (size_t iter = 0;; ++iter) {
        POMAGMA_DEBUG("close step " << iter);
        if (try_close(approx)) {
            return;
        }
    }
}

bool Approximator::try_close (Approximation & approx)
{
    POMAGMA_ASSERT_EQ(approx.lower.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(approx.upper.item_dim(), m_item_dim);

    Approximation start(m_item_dim, m_top, m_bot);
    start = approx;
    DenseSet set(m_item_dim);

    if (approx.ob) {
        approx.upper.insert(approx.ob);
        approx.lower.insert(approx.ob);
    }

    for (auto iter = approx.upper.iter(); iter.ok(); iter.next()) {
        Ob ob = * iter;
        approx.upper += m_less.get_Lx_set(ob);

        if (m_rand) {
            set.set_insn(approx.upper, m_rand->get_Lx_set(ob));
            for (auto iter = set.iter(); iter.ok(); iter.next()) {
                Ob other = * iter;
                if (other >= ob) {
                    break;
                }
                Ob val = m_rand->find(ob, other);
                approx.upper.insert(val);
            }
        }
    }
    approx.upper.insert(m_top);

    for (auto iter = approx.lower.iter(); iter.ok(); iter.next()) {
        Ob ob = * iter;
        approx.lower += m_less.get_Rx_set(ob);

        if (m_join) {
            set.set_insn(approx.lower, m_join->get_Lx_set(ob));
            for (auto iter = set.iter(); iter.ok(); iter.next()) {
                Ob other = * iter;
                if (other >= ob) {
                    break;
                }
                Ob val = m_join->find(ob, other);
                approx.lower.insert(val);
            }
        }

        if (m_rand) {
            set.set_insn(approx.lower, m_rand->get_Lx_set(ob));
            for (auto iter = set.iter(); iter.ok(); iter.next()) {
                Ob other = * iter;
                if (other >= ob) {
                    break;
                }
                Ob val = m_rand->find(ob, other);
                approx.lower.insert(val);
            }
        }
    }
    approx.lower.insert(m_bot);

    return approx == start;
}

Approximation Approximator::find (
        const NullaryFunction & fun)
{
    if (Ob val = fun.find()) {
        return Approximation(val, m_less);
    }
    return Approximation(m_item_dim, m_top, m_bot);
}

Approximation Approximator::find (
        const InjectiveFunction & fun,
        const Approximation & key)
{
    if (Ob ob = key.ob ? fun.find(key.ob) : 0) {
        return Approximation(ob, m_less);
    } else {
        Approximation val(m_item_dim, m_top, m_bot);
        map(fun, key.upper, val.upper);
        map(fun, key.lower, val.lower);
        close(val);
        return val;
    }
}

Approximation Approximator::find (
        const BinaryFunction & fun,
        const Approximation & lhs,
        const Approximation & rhs)
{
    if (Ob ob = lhs.ob and rhs.ob ? fun.find(lhs.ob, rhs.ob) : 0) {
        return Approximation(ob, m_less);
    } else {
        Approximation val(m_item_dim, m_top, m_bot);
        map(fun, lhs.upper, rhs.upper, val.upper);
        map(fun, lhs.lower, rhs.lower, val.lower);
        close(val);
        return val;
    }
}

Approximation Approximator::find (
        const SymmetricFunction & fun,
        const Approximation & lhs,
        const Approximation & rhs)
{
    if (Ob ob = lhs.ob and rhs.ob ? fun.find(lhs.ob, rhs.ob) : 0) {
        return Approximation(ob, m_less);
    } else if (& fun == m_join) {
        Approximation val(m_item_dim, m_top, m_bot);
        val.upper.set_insn(lhs.upper, rhs.upper);
        val.lower.set_union(lhs.lower, rhs.lower);
        return val;
    } else {
        Approximation val(m_item_dim, m_top, m_bot);
        map(fun, lhs.upper, rhs.upper, val.upper);
        map(fun, lhs.lower, rhs.lower, val.lower);
        close(val);
        return val;
    }
}

Approximator::Trool Approximator::is_top (const Approximation & approx)
{
    if (approx.lower.contains(m_top)) {
        return TRUE;
    } if (not (approx.upper.disjoint(m_nless.get_Lx_set(m_top)))) {
        return FALSE;
    } else {
        return MAYBE;
    }
}

Approximator::Trool Approximator::is_bot (const Approximation & approx)
{
    if (approx.upper.contains(m_bot)) {
        return TRUE;
    } if (not (approx.lower.disjoint(m_nless.get_Rx_set(m_bot)))) {
        return FALSE;
    } else {
        return MAYBE;
    }
}

} // namespace pomagma
