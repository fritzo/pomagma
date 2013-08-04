#include "infer.hpp"
#include <pomagma/macrostructure/structure_impl.hpp>
#include <pomagma/macrostructure/scheduler.hpp>
#include <mutex>

#define POMAGMA_ASSERT_UNDECIDED(rel, x, y)\
    POMAGMA_ASSERT(not rel.find(x, y),\
        "already decided " #rel " " << x << " " << y)

namespace pomagma
{

namespace
{

// All the nonconst filtering below is only an optimization.
DenseSet get_nonconst (Structure & structure)
{
    const Carrier & carrier = structure.carrier();
    const NullaryFunction & K = structure.nullary_function("K");
    const BinaryFunction & APP = structure.binary_function("APP");

    POMAGMA_ASSERT_EQ(carrier.item_dim(), carrier.item_count());
    DenseSet nonconst(carrier.item_dim());

    nonconst.complement();
    if (Ob K_ = K.find()) {
        for (auto iter = APP.iter_lhs(K_); iter.ok(); iter.next()) {
            Ob x = * iter;
            Ob APP_K_x = APP.find(K_, x);
            nonconst.remove(APP_K_x);
        }
    }

    return nonconst;
}

inline bool infer_less_transitive (
    const BinaryRelation & LESS,
    Ob x,
    Ob y,
    DenseSet & z_set)
{
    /*
    LESS x z   LESS z y
    -------------------
         LESS x y
    */
    z_set.set_insn(LESS.get_Lx_set(x), LESS.get_Rx_set(y));
    if (unlikely(not z_set.empty())) {
        return true;
    }

    return false;
}

inline bool infer_nless_transitive(
    const BinaryRelation & LESS,
    const BinaryRelation & NLESS,
    Ob x,
    Ob y,
    DenseSet & z_set)
{
    /*
    NLESS x z   LESS y z
    --------------------
         NLESS x y
    */
    z_set.set_insn(NLESS.get_Lx_set(x), LESS.get_Lx_set(y));
    if (unlikely(not z_set.empty())) {
        return true;
    }

    /*
    LESS z x   NLESS z y
    --------------------
          NLESS x y
    */
    z_set.set_insn(LESS.get_Rx_set(x), NLESS.get_Rx_set(y));
    if (unlikely(not z_set.empty())) {
        return true;
    }

    return false;
}

inline void infer_less_monotone(
    BinaryRelation & LESS,
    const BinaryFunction & fun,
    const DenseSet & nonconst,
    Ob x,
    Ob y,
    DenseSet & z_set)
{
    /*
         LESS x y
    --------------------
    LESS fun x z fun y z
    */
    if (nonconst.contains(x) or nonconst.contains(y)) {
        z_set.set_insn(fun.get_Lx_set(x), fun.get_Lx_set(y));
        for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
            Ob z = * iter;
            Ob xz = fun.find(x, z);
            Ob yz = fun.find(y, z);
            LESS.insert(xz, yz);
        }
    }

    /*
         LESS x y
    --------------------
    LESS fun z x fun z y
    */
    z_set.set_insn(fun.get_Rx_set(x), fun.get_Rx_set(y), nonconst);
    for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
        Ob z = * iter;
        Ob zx = fun.find(z, x);
        Ob zy = fun.find(z, y);
        LESS.insert(zx, zy);
    }
}

inline bool infer_nless_monotone(
    const BinaryRelation & NLESS,
    const BinaryFunction & fun,
    const DenseSet & nonconst,
    Ob x,
    Ob y,
    DenseSet & z_set)
{
    /*
    NLESS fun x z fun y z
    ---------------------
          NLESS x y
    */
    if (nonconst.contains(x) or nonconst.contains(y)) {
        z_set.set_insn(fun.get_Lx_set(x), fun.get_Lx_set(y));
        for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
            Ob z = * iter;
            Ob xz = fun.find(x, z);
            Ob yz = fun.find(y, z);
            if (unlikely(NLESS.find(xz, yz))) {
                return true;
            }
        }
    }

    /*
    NLESS fun z x fun z y
    ---------------------
          NLESS x y
    */
    z_set.set_insn(fun.get_Rx_set(x), fun.get_Rx_set(y), nonconst);
    for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
        Ob z = * iter;
        Ob zx = fun.find(z, x);
        Ob zy = fun.find(z, y);
        if (unlikely(NLESS.find(zx, zy))) {
            return true;
        }
    }

    return false;
}

} // anonymous namespace

size_t infer_const (Structure & structure)
{
    POMAGMA_INFO("Inferring K");

    const Carrier & carrier = structure.carrier();
    const NullaryFunction & K = structure.nullary_function("K");
    BinaryFunction & APP = structure.binary_function("APP");
    BinaryFunction & COMP = structure.binary_function("COMP");

    POMAGMA_ASSERT_EQ(carrier.item_dim(), carrier.item_count());
    DenseSet y_set(carrier.item_dim());

    size_t decision_count = 0;
    if (Ob K_ = K.find()) {
        for (auto iter = APP.iter_lhs(K_); iter.ok(); iter.next()) {
            Ob x = * iter;
            Ob APP_K_x = APP.find(K_, x);

            /*
            ---------------------
            EQUAL APP APP K x y x
            */
            y_set.complement(APP.get_Lx_set(APP_K_x));
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                Ob y = * iter;
                APP.insert(APP_K_x, y, x);
                ++decision_count;
            }

            /*
            ----------------------------
            EQUAL COMP APP K x y APP K x
            */
            y_set.complement(COMP.get_Lx_set(APP_K_x));
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                Ob y = * iter;
                COMP.insert(APP_K_x, y, APP_K_x);
                ++decision_count;
            }
        }
    }

    POMAGMA_INFO("inferred " << decision_count << " K facts");
    return decision_count;
}

size_t infer_nless (Structure & structure)
{
    POMAGMA_INFO("Inferring NLESS");

    const Carrier & carrier = structure.carrier();
    const BinaryRelation & LESS = structure.binary_relation("LESS");
    BinaryRelation & NLESS = structure.binary_relation("NLESS");
    const BinaryFunction & APP = structure.binary_function("APP");
    const BinaryFunction & COMP = structure.binary_function("COMP");
    const DenseSet nonconst = get_nonconst(structure);

    POMAGMA_ASSERT_EQ(carrier.item_dim(), carrier.item_count());
    const size_t item_dim = carrier.item_dim();

    size_t decision_count = 0;
    std::mutex mutex;

    #pragma omp parallel for schedule(dynamic)
    for (Ob x = 1; x <= item_dim; ++x) {
        POMAGMA_ASSERT(carrier.contains(x), "unsupported ob: " << x);

        DenseSet y_set(item_dim);
        DenseSet z_set(item_dim);
        DenseSet theorems(item_dim);

        y_set.set_union(NLESS.get_Lx_set(x), LESS.get_Lx_set(x));
        y_set.complement();
        for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
            Ob y = * iter;
            POMAGMA_ASSERT(carrier.contains(y), "unsupported ob: " << y);
            POMAGMA_ASSERT_UNDECIDED(LESS, x, y);
            POMAGMA_ASSERT_UNDECIDED(NLESS, x, y);

            if (infer_nless_transitive(LESS, NLESS, x, y, z_set) or
                infer_nless_monotone(NLESS, APP, nonconst, x, y, z_set) or
                infer_nless_monotone(NLESS, COMP, nonconst, x, y, z_set))
            {
                theorems.insert(y);
            }
        }

        // WARNING this assume writes are atomic and concurrent reads are safe
        std::unique_lock<std::mutex>(mutex);
        for (auto iter = theorems.iter(); iter.ok(); iter.next()) {
            Ob y = * iter;
            NLESS.insert(x, y);
            ++decision_count;
        }
    }

    POMAGMA_INFO("inferred " << decision_count << " NLESS facts");
    return decision_count;
}

size_t infer_less (Structure & structure)
{
    POMAGMA_INFO("Inferring LESS");

    const Carrier & carrier = structure.carrier();
    BinaryRelation & LESS = structure.binary_relation("LESS");
    const BinaryRelation & NLESS = structure.binary_relation("NLESS");
    const BinaryFunction & APP = structure.binary_function("APP");
    const BinaryFunction & COMP = structure.binary_function("COMP");
    const DenseSet nonconst = get_nonconst(structure);

    POMAGMA_ASSERT_EQ(carrier.item_dim(), carrier.item_count());
    DenseSet y_set(carrier.item_dim());
    DenseSet z_set(carrier.item_dim());

    size_t start_count = LESS.count_pairs();

    for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
        Ob x = * iter;

        y_set.set_union(NLESS.get_Lx_set(x), LESS.get_Lx_set(x));
        y_set.complement();
        for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
            Ob y = * iter;
            POMAGMA_ASSERT(carrier.contains(y), "unsupported ob: " << y);
            POMAGMA_ASSERT_UNDECIDED(NLESS, x, y);
            POMAGMA_ASSERT_UNDECIDED(LESS, x, y);

            if (infer_less_transitive(LESS, x, y, z_set)) {
                LESS.insert(x, y);
            }
        }
    }

    for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
        Ob x = * iter;
        for (auto iter = LESS.iter_lhs(x); iter.ok(); iter.next()) {
            Ob y = * iter;

            infer_less_monotone(LESS, APP, nonconst, x, y, z_set);
            infer_less_monotone(LESS, COMP, nonconst, x, y, z_set);
        }
    }

    size_t decision_count = LESS.count_pairs() - start_count;
    POMAGMA_INFO("inferred " << decision_count << " LESS facts");
    return decision_count;
}

size_t infer_equal (Structure & structure)
{
    POMAGMA_INFO("Inferring EQUAL");

    Carrier & carrier = structure.carrier();
    const BinaryRelation & LESS = structure.binary_relation("LESS");

    POMAGMA_ASSERT_EQ(carrier.item_dim(), carrier.item_count());
    DenseSet y_set(carrier.item_dim());

    carrier.set_merge_callback(schedule_merge);

    for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
        Ob x = * iter;

        y_set.set_insn(LESS.get_Lx_set(x), LESS.get_Rx_set(x));
        for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
            Ob y = * iter;
            if (likely(y < x)) {
                carrier.merge(x, y);
            } else {
                break;
            }
        }
    }

    process_mergers(structure.signature());

    size_t decision_count = carrier.item_dim() - carrier.item_count();
    POMAGMA_INFO("inferred " << decision_count << " EQUAL facts");
    return decision_count;
}

size_t infer (Structure & structure)
{
    return
        infer_const(structure) +
        infer_nless(structure) +
        infer_less(structure) +
        infer_equal(structure);
}

} // namespace pomagma
