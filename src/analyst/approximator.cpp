#include "approximator.hpp"
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
      m_identity(structure.nullary_function("I").find()),
      m_less(structure.binary_relation("LESS")),
      m_nless(structure.binary_relation("NLESS")),
      m_join(structure.signature().symmetric_function("JOIN")),
      m_rand(structure.signature().symmetric_function("RAND")),
      m_quote(structure.signature().injective_function("QUOTE"))
{
    POMAGMA_ASSERT(m_top, "TOP is not defined");
    POMAGMA_ASSERT(m_bot, "BOT is not defined");
    POMAGMA_ASSERT(m_identity, "I is not defined");
}

size_t Approximator::test_less ()
{
    POMAGMA_INFO("Testing LESS closure");

    size_t fail_count = 0;

    const size_t item_dim = m_item_dim;
    #pragma omp parallel
    {
        Approximation actual(item_dim, m_top, m_bot);
        DenseSet temp_set(m_item_dim);

        #pragma omp for schedule(dynamic, 1)
        for (Ob x = 1; x <= item_dim; ++x) {
            Approximation expected(x, m_less, m_nless);
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

namespace
{

struct ErrorCounter
{
    size_t fail_count;
    size_t extra_count;
    size_t missing_count;

    ErrorCounter () : fail_count(0), extra_count(0), missing_count(0) {}

    void assert_eq (
            const DenseSet & actual,
            const DenseSet & expected,
            DenseSet & temp_set)
    {
        if (actual != expected) {
            #pragma omp atomic
            fail_count += 1;
            temp_set.set_diff(actual, expected);
            if (size_t count = temp_set.count_items()) {
                #pragma omp atomic
                extra_count += count;
            }
            temp_set.set_diff(expected, actual);
            if (size_t count = temp_set.count_items()) {
                #pragma omp atomic
                missing_count += count;
            }
        }
    }

    void print_warn (const std::string & name) const
    {
        if (fail_count) {
            POMAGMA_WARN(name << " upper has "
                << missing_count << " missing and "
                << extra_count << " extra obs in "
                << fail_count << " cases");
        }
    }
};

} // namespace

template<class Function>
size_t Approximator::test_function (
        const std::string & name,
        const Function & fun)
{
    POMAGMA_INFO("Testing " << name << " approximation");

    size_t ob_fail_count = 0;
    ErrorCounter upper;
    ErrorCounter lower;
    ErrorCounter nupper;
    ErrorCounter nlower;

    const size_t item_dim = m_item_dim;
    #pragma omp parallel
    {
        DenseSet temp_set(item_dim);

        #pragma omp for schedule(dynamic, 1)
        for (Ob x = 1; x <= item_dim; ++x) {
            Approximation approx_x(x, m_less, m_nless);
            approx_x.ob = 0;

            for (auto iter = fun.iter_lhs(x); iter.ok(); iter.next()) {
                Ob y = * iter;
                Approximation approx_y(y, m_less, m_nless);
                approx_y.ob = 0;

                Ob xy = fun.find(x, y);
                Approximation expected(xy, m_less, m_nless);
                Approximation actual = find(fun, approx_x, approx_y);

                if (actual.ob != expected.ob) {
                    #pragma omp atomic
                    ob_fail_count += 1;
                }
                upper.assert_eq(actual.upper, expected.upper, temp_set);
                lower.assert_eq(actual.lower, expected.lower, temp_set);
                nupper.assert_eq(actual.nupper, expected.nupper, temp_set);
                nlower.assert_eq(actual.nlower, expected.nlower, temp_set);
            }
        }
    }

    if (ob_fail_count) {
        POMAGMA_WARN(name << " ob failed " << ob_fail_count << " cases");
    }
    upper.print_warn(name);
    lower.print_warn(name);
    nupper.print_warn(name);
    nlower.print_warn(name);

    return ob_fail_count + upper.fail_count + lower.fail_count
                         + nupper.fail_count + nlower.fail_count;
}

size_t Approximator::test ()
{
    POMAGMA_INFO("Testing approximator");

    size_t fail_count = 0;

    fail_count += test_less();
    for (auto pair : m_structure.signature().binary_functions()) {
        fail_count += test_function(pair.first, * pair.second);
    }
    for (auto pair : m_structure.signature().symmetric_functions()) {
        fail_count += test_function(pair.first, * pair.second);
    }

    if (fail_count) {
        POMAGMA_WARN("Failed approximator test");
    } else {
        POMAGMA_INFO("Passed approximator test");
    }

    return fail_count;
}

void Approximator::validate (const Approximation & approx)
{
    POMAGMA_ASSERT_EQ(approx.lower.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(approx.upper.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(approx.nlower.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(approx.nupper.item_dim(), m_item_dim);

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

    Approximation closed = unknown();
    closed = approx;
    {
        DenseSet temp_set(m_item_dim);
        close(closed, temp_set);
    }
    POMAGMA_ASSERT_EQ(closed.ob, approx.ob);
    POMAGMA_ASSERT(closed.upper == approx.upper, "upper set is not closed");
    POMAGMA_ASSERT(closed.lower == approx.lower, "lower set is not closed");
    POMAGMA_ASSERT(closed.nupper == approx.nupper, "nupper set is not closed");
    POMAGMA_ASSERT(closed.nlower == approx.nlower, "nlower set is not closed");
}

void Approximator::close (
        Approximation & approx,
        DenseSet & temp_set)
{
    // TODO this could be more efficient by recording the diff and propagating
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
    POMAGMA_ASSERT_EQ(approx.nlower.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(approx.nupper.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(temp_set.item_dim(), m_item_dim);

    Approximation start = unknown();
    start = approx;

    if (approx.ob) {
        approx.upper += m_less.get_Lx_set(approx.ob);
        approx.lower += m_less.get_Rx_set(approx.ob);
        approx.nupper += m_nless.get_Lx_set(approx.ob);
        approx.nlower += m_nless.get_Rx_set(approx.ob);
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

    // TODO use iter_insn() instead of set_diff();iter()
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

        // this is an optimization for the special cases of APP and COMP
        if (Ob lhs_top = fun.find(lhs, m_top)) {
            if (Ob lhs_bot = fun.find(lhs, m_bot)) {
                bool lhs_is_constant = (lhs_top == lhs_bot);
                if (lhs_is_constant) {
                    val_set.raw_insert(lhs_top);
                    continue;
                }
            }
        }

        // TODO use iter_diff() instead of set_diff();iter()
        temp_set.set_insn(rhs_set, fun.get_Lx_set(lhs));
        for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
            Ob rhs = * iter;
            Ob val = fun.find(lhs, rhs);
            val_set.raw_insert(val);
        }
    }
}

inline void Approximator::map_lhs_val (
        const BinaryFunction & fun,
        const DenseSet & lhs_pos_set,
        DenseSet & rhs_neg_set,
        const DenseSet & val_neg_set,
        DenseSet & temp_set)
{
    POMAGMA_ASSERT_EQ(lhs_pos_set.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(rhs_neg_set.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(val_neg_set.item_dim(), m_item_dim);
    POMAGMA_ASSERT_EQ(temp_set.item_dim(), m_item_dim);

    for (auto iter = lhs_pos_set.iter(); iter.ok(); iter.next()) {
        Ob lhs = * iter;

        // TODO optimize for the special cases of APP and COMP

        // TODO use iter_diff() instead of set_diff();iter()
        temp_set.set_diff(fun.get_Lx_set(lhs), rhs_neg_set);
        for (auto iter = temp_set.iter(); iter.ok(); iter.next()) {
            Ob rhs = * iter;
            Ob val = fun.find(lhs, rhs);
            if (val_neg_set.contains(val)) {
                rhs_neg_set.raw_insert(rhs);
                break;
            }
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
        // TODO use iter_insn() instead of set_diff();iter()
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
        return Approximation(val, m_less, m_nless);
    }
    return unknown();
}

Approximation Approximator::find (
        const InjectiveFunction & fun,
        const Approximation & key)
{
    if (Ob ob = key.ob ? fun.find(key.ob) : 0) {
        return Approximation(ob, m_less, m_nless);
    } else if (& fun == m_quote) {
        // QUOTE is not monotone
        return unknown();
    } else {
        Approximation val = unknown();
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
        return Approximation(ob, m_less, m_nless);
    } else {
        Approximation val = unknown();
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
        return Approximation(ob, m_less, m_nless);
    } else {
        Approximation val = unknown();
        DenseSet temp_set(m_item_dim);
        map(fun, lhs.upper, rhs.upper, val.upper, temp_set);
        map(fun, lhs.lower, rhs.lower, val.lower, temp_set);
        close(val, temp_set);
        return val;
    }
}

Approximation Approximator::find (
        const UnaryRelation & pos,
        const UnaryRelation & neg,
        const Approximation & arg)
{
    if (arg.ob and pos.find(arg.ob)) {
        return truthy();
    } else if (arg.ob and neg.find(arg.ob)) {
        return falsey();
    } else {
        return maybe();
    }
}

Approximation Approximator::find (
        const BinaryRelation & pos,
        const BinaryRelation & neg,
        const Approximation & lhs,
        const Approximation & rhs)
{
    if (lhs.ob and rhs.ob and pos.find(lhs.ob, rhs.ob)) {
        return truthy();
    } else if (lhs.ob and rhs.ob and neg.find(lhs.ob, rhs.ob)) {
        return falsey();
    } else {
        return maybe();
    }
}

Approximation Approximator::find (
        const std::string & name)
{
    Signature & signature = m_structure.signature();
    if (auto * fun = signature.nullary_function(name)) {
        return find(* fun);
    } else {
        return unknown();
    }
}

Approximation Approximator::find (
        const std::string & name,
        const Approximation & arg0)
{
    Signature & signature = m_structure.signature();
    if (auto * fun = signature.injective_function(name)) {
        return find(* fun, arg0);
    } else if (auto * pos = signature.unary_relation(name)) {
        std::string negated = signature.negate(name);
        if (auto * neg = signature.unary_relation(negated)) {
            return find(* pos, * neg, arg0);
        } else {
            return unknown();
        }
    } else {
        return unknown();
    }
}

Approximation Approximator::find (
        const std::string & name,
        const Approximation & arg0,
        const Approximation & arg1)
{
    Signature & signature = m_structure.signature();
    if (auto * fun = signature.binary_function(name)) {
        return find(* fun, arg0, arg1);
    } else if (auto * fun = signature.symmetric_function(name)) {
        return find(* fun, arg0, arg1);
    } else if (auto * pos = signature.binary_relation(name)) {
        std::string negated = signature.negate(name);
        if (auto * neg = signature.binary_relation(negated)) {
            return find(* pos, * neg, arg0, arg1);
        } else {
            return unknown();
        }
    } else {
        return unknown();
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
