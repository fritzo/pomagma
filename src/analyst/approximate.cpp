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


template<class Function>
size_t Approximator::validate_function (
        const std::string & name,
        const Function & fun)
{
    POMAGMA_INFO("Validating " << name << " approximation");

    size_t ob_fail_count;
    size_t upper_fail_count = 0;
    size_t lower_fail_count = 0;

    const size_t item_dim = m_item_dim;
    #pragma omp parallel for schedule(dynamic, 1)
    for (Ob x = 1; x <= item_dim; ++x) {
        Approximation approx_x(x, m_less);
        approx_x.ob = 0;

        for (auto iter = fun.iter_lhs(x); iter.ok(); iter.next()) {
            Ob y = * iter;
            Approximation approx_y(y, m_less);
            approx_y.ob = 0;

            Ob xy = fun.find(x, y);
            Approximation expected(xy, m_less);
            Approximation actual = find(fun, approx_x, approx_y);

            if (actual.ob != expected.ob) {
                #pragma omp atomic
                ob_fail_count += 1;
            }
            if (actual.upper != expected.upper) {
                #pragma omp atomic
                upper_fail_count += 1;
            }
            if (actual.lower != expected.lower) {
                #pragma omp atomic
                lower_fail_count += 1;
            }
        }
    }

    if (ob_fail_count) {
        POMAGMA_WARN("failed " << ob_fail_count << " ob cases");
    }
    if (upper_fail_count) {
        POMAGMA_WARN("failed " << upper_fail_count << " upper cases");
    }
    if (lower_fail_count) {
        POMAGMA_WARN("failed " << lower_fail_count << " lower cases");
    }

    return ob_fail_count + upper_fail_count + lower_fail_count;
}

size_t Approximator::validate ()
{
    POMAGMA_INFO("Validating approximator");

    size_t fail_count = 0;

    for (auto pair : m_structure.signature().binary_functions()) {
        fail_count += validate_function(pair.first, * pair.second);
    }
    for (auto pair : m_structure.signature().symmetric_functions()) {
        fail_count += validate_function(pair.first, * pair.second);
    }

    POMAGMA_INFO("approximator is " << (fail_count ? "invalid" : "valid"));

    return fail_count;
}

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

// Inference rules, in order of appearance
//
//   LESS x y   LESS x z
//   -------------------   ----------
//     LESS x RAND y z     LESS x TOP
//   
//   LESS y x   LESS z x   LESS y x   LESS z x
//   -------------------   -------------------   ----------
//     LESS JOIN y z x       LESS RAND y z x     LESS BOT x
//
bool Approximator::try_close (Approximation & approx)
{
    POMAGMA_ASSERT_EQ(approx.lower.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(approx.upper.item_dim(), m_item_dim);

    Approximation start(m_item_dim, m_top, m_bot);
    start = approx;
    DenseSet set(m_item_dim);

    if (not approx.ob) {
        set.set_insn(approx.upper, approx.lower);
        for (auto iter = set.iter(); iter.ok(); iter.next()) {
            approx.ob = * iter;
            break;
        }
    }

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
    } if (approx.upper.intersects(m_nless.get_Lx_set(m_top))) {
        return FALSE;
    } else {
        return MAYBE;
    }
}

Approximator::Trool Approximator::is_bot (const Approximation & approx)
{
    if (approx.upper.contains(m_bot)) {
        return TRUE;
    } if (approx.lower.intersects(m_nless.get_Rx_set(m_bot))) {
        return FALSE;
    } else {
        return MAYBE;
    }
}

} // namespace pomagma
