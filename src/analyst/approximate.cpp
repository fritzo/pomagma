#include "approximate.hpp"
#include <vector>

#define POMAGMA_DEBUG1(message)
//#define POMAGMA_DEBUG1 POMAGMA_DEBUG

namespace pomagma
{

Approximator::Approximator (Structure & structure)
    : m_structure(structure),
      m_item_dim(structure.carrier().item_dim()),
      m_top(structure.nullary_function("TOP").find()),
      m_bot(structure.nullary_function("BOT").find()),
      m_less(structure.binary_relation("LESS")),
      m_nless(structure.binary_relation("NLESS")),
      m_join(structure.signature().symmetric_function("JOIN")),
      m_rand(structure.signature().symmetric_function("RAND")),
      m_quote(structure.signature().injective_function("QUOTE"))
{
    POMAGMA_ASSERT(m_top, "TOP is not defined");
    POMAGMA_ASSERT(m_bot, "BOT is not defined");
}

size_t Approximator::validate_less ()
{
    POMAGMA_INFO("Validating LESS closure");

    size_t fail_count = 0;

    const size_t item_dim = m_item_dim;
    #pragma omp parallel
    {
        Approximation actual(item_dim, m_top, m_bot);
        DenseSet temp_set(m_item_dim);

        #pragma omp for schedule(dynamic, 1)
        for (Ob x = 1; x <= item_dim; ++x) {
            Approximation expected(x, m_less);
            actual = expected;
            close(actual, temp_set);

            if (actual != expected) {
                #pragma omp atomic
                fail_count += 1;
            }
        }
    }

    if (fail_count) {
        POMAGMA_WARN("LESS failed " << fail_count << " cases");
    }

    return fail_count;
}

template<class Function>
size_t Approximator::validate_function (
        const std::string & name,
        const Function & fun)
{
    POMAGMA_INFO("Validating " << name << " approximation");

    size_t ob_fail_count = 0;
    size_t upper_fail_count = 0;
    size_t upper_extra_count = 0;
    size_t upper_missing_count = 0;
    size_t lower_fail_count = 0;
    size_t lower_extra_count = 0;
    size_t lower_missing_count = 0;

    const size_t item_dim = m_item_dim;
    #pragma omp parallel
    {
        DenseSet temp_set(item_dim);

        #pragma omp for schedule(dynamic, 1)
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
                    temp_set.set_diff(actual.upper, expected.upper);
                    if (size_t count = temp_set.count_items()) {
                        #pragma omp atomic
                        upper_extra_count += count;
                    }
                    temp_set.set_diff(expected.upper, actual.upper);
                    if (size_t count = temp_set.count_items()) {
                        #pragma omp atomic
                        upper_missing_count += count;
                    }
                }
                if (actual.lower != expected.lower) {
                    #pragma omp atomic
                    lower_fail_count += 1;
                    temp_set.set_diff(actual.lower, expected.lower);
                    if (size_t count = temp_set.count_items()) {
                        #pragma omp atomic
                        lower_extra_count += count;
                    }
                    temp_set.set_diff(expected.lower, actual.lower);
                    if (size_t count = temp_set.count_items()) {
                        #pragma omp atomic
                        lower_missing_count += count;
                    }
                }
            }
        }
    }

    if (ob_fail_count) {
        POMAGMA_WARN(name << "-mapped ob failed "
            << ob_fail_count << " cases");
    }
    if (upper_missing_count or upper_extra_count) {
        POMAGMA_WARN(name << "-mapped upper had "
            << upper_missing_count << " missing and "
            << upper_extra_count << " extra obs in "
            << upper_fail_count << " cases");
    }
    if (lower_missing_count or lower_extra_count) {
        POMAGMA_WARN(name << "-mapped lower had "
            << lower_missing_count << " missing and "
            << lower_extra_count << " extra obs in "
            << lower_fail_count << " cases");
    }

    return ob_fail_count + upper_fail_count + lower_fail_count;
}

size_t Approximator::validate ()
{
    POMAGMA_INFO("Validating approximator");

    size_t fail_count = 0;

    fail_count += validate_less();
    for (auto pair : m_structure.signature().binary_functions()) {
        fail_count += validate_function(pair.first, * pair.second);
    }
    for (auto pair : m_structure.signature().symmetric_functions()) {
        fail_count += validate_function(pair.first, * pair.second);
    }

    if (fail_count) {
        POMAGMA_WARN("approximator is invalid");
    } else {
        POMAGMA_INFO("approximator is valid");
    }

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
    {
        DenseSet temp_set(m_item_dim);
        close(closed, temp_set);
    }
    POMAGMA_ASSERT_EQ(closed.ob, approx.ob);
    POMAGMA_ASSERT(closed.upper == approx.upper, "upper set is not closed");
    POMAGMA_ASSERT(closed.lower == approx.lower, "lower set is not closed");
}

void Approximator::close (
        Approximation & approx,
        DenseSet & temp_set)
{
    POMAGMA_ASSERT_EQ(temp_set.item_dim(), m_item_dim);
    for (size_t iter = 0;; ++iter) {
        POMAGMA_DEBUG1("close step " << iter);
        if (try_close(approx, temp_set)) {
            return;
        }
    }
}

// Inference rules, in order of appearance
//
//                LESS x y   LESS x z
//   ----------   -------------------
//   LESS x TOP     LESS x RAND y z
//   
//                LESS y x   LESS z x   LESS y x   LESS z x
//   ----------   -------------------   -------------------
//   LESS BOT x     LESS JOIN y z x       LESS RAND y z x
//
bool Approximator::try_close (
        Approximation & approx,
        DenseSet & temp_set)
{
    POMAGMA_ASSERT_EQ(approx.lower.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(approx.upper.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(temp_set.item_dim(), m_item_dim);

    Approximation start(m_item_dim, m_top, m_bot);
    start = approx;

    if (approx.ob) {
        approx.upper.raw_insert(approx.ob);
        approx.lower.raw_insert(approx.ob);
    }

    approx.upper.raw_insert(m_top);
    for (auto iter = approx.upper.iter(); iter.ok(); iter.next()) {
        Ob ob = * iter;
        approx.upper += m_less.get_Lx_set(ob);

        if (m_rand) {
            temp_set.set_insn(approx.upper, m_rand->get_Lx_set(ob));
            for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
                Ob other = * iter;
                if (other >= ob) {
                    break;
                }
                Ob val = m_rand->find(ob, other);
                approx.upper.raw_insert(val);
            }
        }
    }

    approx.lower.raw_insert(m_bot);
    for (auto iter = approx.lower.iter(); iter.ok(); iter.next()) {
        Ob ob = * iter;
        approx.lower += m_less.get_Rx_set(ob);

        if (m_join) {
            temp_set.set_insn(approx.lower, m_join->get_Lx_set(ob));
            for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
                Ob other = * iter;
                if (other >= ob) {
                    break;
                }
                Ob val = m_join->find(ob, other);
                approx.lower.raw_insert(val);
            }
        }

        if (m_rand) {
            temp_set.set_insn(approx.lower, m_rand->get_Lx_set(ob));
            for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
                Ob other = * iter;
                if (other >= ob) {
                    break;
                }
                Ob val = m_rand->find(ob, other);
                approx.lower.raw_insert(val);
            }
        }
    }

    if (not approx.ob) {
        temp_set.set_insn(approx.upper, approx.lower);
        for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
            approx.ob = * iter;
            break;
        }
    }

    return approx == start;
}


inline void Approximator::map (
        const InjectiveFunction & fun,
        const DenseSet & key_set,
        DenseSet & val_set,
        DenseSet & temp_set)
{
    POMAGMA_ASSERT_EQ(key_set.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(val_set.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(temp_set.item_dim(), m_item_dim);

    temp_set.set_insn(fun.defined(), key_set);
    for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
        Ob key = * iter;
        Ob val = fun.find(key);
        val_set.raw_insert(val);
    }
}

inline void Approximator::map (
        const BinaryFunction & fun,
        const DenseSet & lhs_set,
        const DenseSet & rhs_set,
        DenseSet & val_set,
        DenseSet & temp_set)
{
    POMAGMA_ASSERT_EQ(lhs_set.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(rhs_set.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(val_set.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(temp_set.item_dim(), m_item_dim);

    for (auto iter = lhs_set.iter(); iter.ok(); iter.next()) {
        Ob lhs = * iter;

        // optimize for special cases of APP and COMP
        if (Ob lhs_top = fun.find(lhs, m_top)) {
            if (Ob lhs_bot = fun.find(lhs, m_bot)) {
                bool lhs_is_constant = (lhs_top == lhs_bot);
                if (lhs_is_constant) {
                    val_set.raw_insert(lhs_top);
                    continue;
                }
            }
        }

        temp_set.set_insn(rhs_set, fun.get_Lx_set(lhs));
        for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
            Ob rhs = * iter;
            Ob val = fun.find(lhs, rhs);
            val_set.raw_insert(val);
        }
    }
}

inline void Approximator::map (
        const SymmetricFunction & fun,
        const DenseSet & lhs_set,
        const DenseSet & rhs_set,
        DenseSet & val_set,
        DenseSet & temp_set)
{
    POMAGMA_ASSERT_EQ(lhs_set.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(rhs_set.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(val_set.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(temp_set.item_dim(), m_item_dim);

    for (auto iter = lhs_set.iter(); iter.ok(); iter.next()) {
        Ob lhs = * iter;
        temp_set.set_insn(rhs_set, fun.get_Lx_set(lhs));
        for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
            Ob rhs = * iter;
            Ob val = fun.find(lhs, rhs);
            val_set.raw_insert(val);
        }
    }
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
    } else if (& fun == m_quote) {
        // QUOTE is not monotone
        return Approximation(m_item_dim, m_top, m_bot);
    } else {
        Approximation val(m_item_dim, m_top, m_bot);
        DenseSet temp_set(m_item_dim);
        map(fun, key.upper, val.upper, temp_set);
        map(fun, key.lower, val.lower, temp_set);
        close(val, temp_set);
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
        DenseSet temp_set(m_item_dim);
        map(fun, lhs.upper, rhs.upper, val.upper, temp_set);
        map(fun, lhs.lower, rhs.lower, val.lower, temp_set);
        close(val, temp_set);
        return val;
    }
}

Approximation Approximator::find (
        const SymmetricFunction & fun,
        const Approximation & lhs,
        const Approximation & rhs)
{
    if (Ob ob = (lhs.ob and rhs.ob) ? fun.find(lhs.ob, rhs.ob) : 0) {
        return Approximation(ob, m_less);
    } else {
        Approximation val(m_item_dim, m_top, m_bot);
        DenseSet temp_set(m_item_dim);
        map(fun, lhs.upper, rhs.upper, val.upper, temp_set);
        map(fun, lhs.lower, rhs.lower, val.lower, temp_set);
        close(val, temp_set);
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
