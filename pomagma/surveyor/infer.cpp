#include "infer.hpp"

#include <pomagma/atlas/micro/scheduler.hpp>
#include <pomagma/atlas/micro/structure_impl.hpp>

#define POMAGMA_ASSERT_UNDECIDED(rel, x, y) \
    POMAGMA_ASSERT(not(rel).find(x, y),     \
                   "already decided " #rel " " << x << " " << y)

namespace pomagma {

Structure& get_structure();  // defined in theory.cpp

namespace {

// All the nonconst filtering below is only an optimization.
DenseSet get_nonconst(Structure& structure) {
    const Carrier& carrier = structure.carrier();
    const NullaryFunction* K = structure.signature().nullary_function("K");
    const BinaryFunction* APP = structure.signature().binary_function("APP");

    DenseSet nonconst(carrier.item_dim());
    nonconst = carrier.support();
    if (K && APP) {
        Ob K_val = K->find();
        if (K_val) {
            for (auto iter = APP->iter_lhs(K_val); iter.ok(); iter.next()) {
                Ob x = *iter;
                Ob APP_K_x = APP->find(K_val, x);
                nonconst.remove(APP_K_x);
            }
        }
    }

    size_t total_count = carrier.item_count();
    size_t const_count = total_count - nonconst.count_items();
    POMAGMA_INFO("found " << const_count << " / " << total_count
                          << " constant obs");

    return nonconst;
}

// NLESS fun x z fun y z   NLESS fun z x fun z y
// ---------------------   ---------------------
//       NLESS x y               NLESS x y
inline bool infer_nless_monotone(const BinaryRelation& NLESS,
                                 const BinaryFunction& fun,
                                 const DenseSet& nonconst, Ob x, Ob y,
                                 DenseSet& z_set) {
    if (nonconst(x)) {
        if (nonconst(y)) {
            z_set.set_insn(fun.get_Lx_set(x), fun.get_Lx_set(y));
            for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
                Ob z = *iter;
                Ob xz = fun.find(x, z);
                Ob yz = fun.find(y, z);
                if (unlikely(NLESS.find(xz, yz))) {
                    return true;
                }
            }
        } else if (Ob y_ = fun.find(y, y)) {
            DenseSet nless = NLESS.get_Rx_set(y_);
            for (auto iter = fun.iter_lhs(x); iter.ok(); iter.next()) {
                Ob z = *iter;
                Ob xz = fun.find(x, z);
                if (unlikely(nless.contains(xz))) {
                    return true;
                }
            }
        }
    } else if (Ob x_ = fun.find(x, x)) {
        if (nonconst(y)) {
            DenseSet nless = NLESS.get_Lx_set(x_);
            for (auto iter = fun.iter_lhs(y); iter.ok(); iter.next()) {
                Ob z = *iter;
                Ob yz = fun.find(y, z);
                if (unlikely(nless.contains(yz))) {
                    return true;
                }
            }
        }
    }

    z_set.set_insn(fun.get_Rx_set(x), fun.get_Rx_set(y), nonconst);
    for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
        Ob z = *iter;
        Ob zx = fun.find(z, x);
        Ob zy = fun.find(z, y);
        if (unlikely(NLESS.find(zx, zy))) {
            return true;
        }
    }

    return false;
}

// NLESS fun x z fun y z
// ---------------------
//       NLESS x y
inline bool infer_nless_monotone(const BinaryRelation& NLESS,
                                 const SymmetricFunction& fun, Ob x, Ob y,
                                 DenseSet& z_set) {
    z_set.set_insn(fun.get_Lx_set(x), fun.get_Lx_set(y));
    for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
        Ob z = *iter;
        Ob xz = fun.find(x, z);
        Ob yz = fun.find(y, z);
        if (unlikely(NLESS.find(xz, yz))) {
            return true;
        }
    }

    return false;
}

}  // namespace

size_t infer_nless() {
    Structure& structure = get_structure();
    Signature& signature = structure.signature();
    const Carrier& carrier = structure.carrier();
    const BinaryRelation& LESS = structure.binary_relation("LESS");
    BinaryRelation& NLESS = structure.binary_relation("NLESS");
    const BinaryFunction& APP = structure.binary_function("APP");
    const BinaryFunction& COMP = structure.binary_function("COMP");
    const SymmetricFunction* JOIN = signature.symmetric_function("JOIN");
    const SymmetricFunction* RAND = signature.symmetric_function("RAND");
    const DenseSet nonconst = get_nonconst(structure);
    const size_t item_dim = carrier.item_dim();

    std::atomic_size_t theorem_count = 0;

#pragma omp parallel
    {
        DenseSet y_set(item_dim);
        DenseSet z_set(item_dim);
        size_t local_count = 0;

#pragma omp for schedule(dynamic, 1)
        for (Ob x = 1; x <= item_dim; ++x) {
            if (not carrier.contains(x)) {
                continue;
            }

            y_set.set_pnn(carrier.support(), LESS.get_Lx_set(x),
                          NLESS.get_Lx_set(x));
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                Ob y = *iter;
                POMAGMA_ASSERT(carrier.contains(y), "unsupported ob: " << y);
                POMAGMA_ASSERT_UNDECIDED(LESS, x, y);
                POMAGMA_ASSERT_UNDECIDED(NLESS, x, y);

                if (infer_nless_monotone(NLESS, APP, nonconst, x, y, z_set) or
                    infer_nless_monotone(NLESS, COMP, nonconst, x, y, z_set) or
                    (JOIN and
                     infer_nless_monotone(NLESS, *JOIN, x, y, z_set)) or
                    (RAND and
                     infer_nless_monotone(NLESS, *RAND, x, y, z_set))) {
                    NLESS.insert(x, y);
                    schedule(NegativeOrderTask(x, y));
                    ++local_count;
                }
            }
        }
        theorem_count.fetch_add(local_count, std::memory_order_acq_rel);
    }

    POMAGMA_INFO("inferred " << theorem_count << " NLESS facts");
    return theorem_count;
}

}  // namespace pomagma