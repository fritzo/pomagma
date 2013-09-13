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

class TheoremQueue
{
    BinaryRelation & m_rel;
    std::vector<std::pair<Ob, Ob>> m_queue;

public:

    TheoremQueue (BinaryRelation & rel) : m_rel(rel) {}
    ~TheoremQueue ()
    {
        POMAGMA_ASSERT(m_queue.empty(), "theorems have not been flushed");
    }

    void push (Ob x, Ob y)
    {
        m_queue.push_back(std::make_pair(x, y));
    }

    void try_push (Ob x, Ob y)
    {
        if (unlikely(not m_rel.find(x, y))) {
            push(x, y);
        }
    }

    void flush (std::mutex & mutex)
    {
        if (not m_queue.empty()) {
            {
                std::unique_lock<std::mutex> lock(mutex);
                for (const auto & pair : m_queue) {
                    m_rel.insert(pair.first, pair.second);
                }
            }
            m_queue.clear();
        }
    }
};

class LhsFixedTheoremQueue
{
    BinaryRelation & m_rel;
    Ob m_lhs;
    DenseSet m_rhs;

public:

    LhsFixedTheoremQueue (BinaryRelation & rel)
        : m_rel(rel),
          m_lhs(0),
          m_rhs(rel.item_dim())
    {
    }

    void push (Ob lhs, Ob rhs)
    {
        POMAGMA_ASSERT1(
            m_lhs == 0 or m_lhs == lhs,
            "mismatched lhs in LhsFixedTheoremQueue; use TheoremQueue instead");
        m_lhs = lhs;
        m_rhs.insert(rhs);
    }

    void flush (std::mutex & mutex)
    {
        if (m_lhs) {
            {
                std::unique_lock<std::mutex> lock(mutex);
                m_rel.insert(m_lhs, m_rhs);
            }
            m_lhs = 0;
            m_rhs.zero();
        }
    }
};

// All the nonconst filtering below is only an optimization.
// Specifically, in rules like
//
//        LESS x y
//   --------------------
//   LESS APP f x APP f y
//
// we skip trivial values f = K z for any z, since K z x = z = K z y.
DenseSet get_nonconst (Structure & structure)
{
    const Carrier & carrier = structure.carrier();
    const NullaryFunction & K = structure.nullary_function("K");
    const BinaryFunction & APP = structure.binary_function("APP");

    DenseSet nonconst(carrier.item_dim());
    nonconst = carrier.support();
    if (Ob K_ = K.find()) {
        for (auto iter = APP.iter_lhs(K_); iter.ok(); iter.next()) {
            Ob x = * iter;
            Ob APP_K_x = APP.find(K_, x);
            nonconst.remove(APP_K_x);
        }
    }

    return nonconst;
}

// LESS x z   LESS z y
// -------------------
//      LESS x y
void infer_less_transitive (
    const Carrier & carrier,
    BinaryRelation & LESS,
    const BinaryRelation & NLESS)
{
    POMAGMA_INFO("Inferring LESS-transitive");

    const size_t item_dim = carrier.item_dim();

    std::mutex mutex;
    #pragma omp parallel
    {
        DenseSet y_set(item_dim);
        LhsFixedTheoremQueue theorems(LESS);

        #pragma omp for schedule(dynamic, 1)
        for (Ob x = 1; x <= item_dim; ++x) {
            const DenseSet less_x = LESS.get_Lx_set(x);

            y_set.set_pnn(
                carrier.support(),
                LESS.get_Lx_set(x),
                NLESS.get_Lx_set(x));
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                Ob y = * iter;
                POMAGMA_ASSERT(carrier.contains(y), "unsupported ob: " << y);
                POMAGMA_ASSERT_UNDECIDED(NLESS, x, y);
                POMAGMA_ASSERT_UNDECIDED(LESS, x, y);

                if (unlikely(not less_x.disjoint(LESS.get_Rx_set(y)))) {
                    theorems.push(x, y);
                }
            }

            theorems.flush(mutex);
        }
    }
}

//      LESS f g               LESS x y          LESS f g    LESS x y
// --------------------   --------------------   --------------------
// LESS fun f x fun g x   LESS fun f x fun f y   LESS fun f x fun g y
void infer_less_monotone (
    BinaryRelation & LESS,
    const BinaryFunction & fun,
    const DenseSet & nonconst)
{
    POMAGMA_INFO("Inferring LESS-monotone");

    const size_t item_dim = nonconst.item_dim();
    std::vector<Ob> f_set;
    for (auto iter = nonconst.iter(); iter.ok(); iter.next()) {
        Ob f = * iter;
        f_set.push_back(f);
    }
    const size_t f_count = f_set.size();

    std::mutex mutex;
    #pragma omp parallel
    {
        DenseSet g_set(item_dim);
        DenseSet x_set(item_dim);
        DenseSet y_set(item_dim);
        TheoremQueue theorems(LESS);

        #pragma omp for schedule(dynamic, 1)
        for (size_t iter = 0; iter < f_count; ++iter) {
            Ob f = f_set[iter];

            g_set.set_insn(nonconst, LESS.get_Lx_set(f));
            g_set.remove(f);
            for (auto iter = g_set.iter(); iter.ok(); iter.next()) {
                Ob g = * iter;

                x_set.set_insn(fun.get_Lx_set(f), fun.get_Lx_set(g));
                for (auto iter = x_set.iter(); iter.ok(); iter.next()) {
                    Ob x = * iter;
                    Ob fx = fun.find(f, x);
                    Ob gx = fun.find(g, x);
                    theorems.try_push(fx, gx);
                }

                x_set.set_diff(fun.get_Lx_set(f), fun.get_Lx_set(g));
                for (auto iter = x_set.iter(); iter.ok(); iter.next()) {
                    Ob x = * iter;
                    Ob fx = fun.find(f, x);
                    const DenseSet less_fx = LESS.get_Lx_set(fx);
                    y_set.set_diff(fun.get_Lx_set(g), fun.get_Lx_set(f));
                    y_set *= LESS.get_Lx_set(x);
                    for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                        Ob y = * iter;
                        Ob gy = fun.find(g, y);
                        if (unlikely(not less_fx(gy))) {
                            theorems.push(fx, gy);
                        }
                    }
                }
            }

            for (auto iter = fun.iter_lhs(f); iter.ok(); iter.next()) {
                Ob x = * iter;
                Ob fx = fun.find(f, x);
                y_set.set_insn(fun.get_Lx_set(f), LESS.get_Lx_set(x));
                y_set.remove(x);
                for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                    Ob y = * iter;
                    Ob fy = fun.find(f, y);
                    theorems.try_push(fx, fy);
                }
            }

            theorems.flush(mutex);
        }
    }
}

// LESS x z   LESS y z
// -------------------
//   LESS JOIN x y z
void infer_less_convex (
    const Carrier & carrier,
    BinaryRelation & LESS,
    const SymmetricFunction & JOIN)
{
    POMAGMA_INFO("Inferring LESS-JOIN-convex");

    const size_t item_dim = carrier.item_dim();
    std::mutex mutex;
    #pragma omp parallel
    {
        DenseSet z_set(item_dim);
        DenseSet y_set(item_dim);
        TheoremQueue theorems(LESS);

        #pragma omp for schedule(dynamic, 1)
        for (Ob x = 1; x <= item_dim; ++x) {
            if (not carrier.contains(x)) { continue; }

            y_set.set_pnn(
                JOIN.get_Lx_set(x),
                LESS.get_Lx_set(x),
                LESS.get_Rx_set(x));
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                Ob y = * iter;
                if (y >= x) {
                    break;
                }
                Ob xy = JOIN.find(x, y);
                z_set.set_ppn(
                    LESS.get_Lx_set(x),
                    LESS.get_Lx_set(y),
                    LESS.get_Lx_set(xy));
                for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
                    Ob z = * iter;
                    theorems.push(xy, z);
                }
            }

            theorems.flush(mutex);
        }
    }
}

//  LESS x z   LESS y z   LESS z x   LESS z y
//  -------------------   -------------------
//    LESS RAND x y z       LESS z RAND x y
void infer_less_linear (
    const Carrier & carrier,
    BinaryRelation & LESS,
    const SymmetricFunction & RAND)
{
    POMAGMA_INFO("Inferring LESS-RAND-linear");

    const size_t item_dim = carrier.item_dim();
    std::mutex mutex;
    #pragma omp parallel
    {
        DenseSet z_set(item_dim);
        DenseSet y_set(item_dim);
        TheoremQueue theorems(LESS);

        #pragma omp for schedule(dynamic, 1)
        for (Ob x = 1; x <= item_dim; ++x) {
            if (not carrier.contains(x)) { continue; }

            y_set.set_pnn(
                RAND.get_Lx_set(x),
                LESS.get_Lx_set(x),
                LESS.get_Rx_set(x));
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                Ob y = * iter;
                if (y >= x) {
                    break;
                }
                Ob xy = RAND.find(x, y);

                z_set.set_ppn(
                    LESS.get_Lx_set(x),
                    LESS.get_Lx_set(y),
                    LESS.get_Lx_set(xy));
                for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
                    Ob z = * iter;
                    theorems.push(xy, z);
                }

                z_set.set_ppn(
                    LESS.get_Rx_set(x),
                    LESS.get_Rx_set(y),
                    LESS.get_Rx_set(xy));
                for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
                    Ob z = * iter;
                    theorems.push(z, xy);
                }
            }

            theorems.flush(mutex);
        }
    }
}

// NLESS x z   LESS y z   LESS z x   NLESS z y
// --------------------   --------------------
//      NLESS x y               NLESS x y
inline bool infer_nless_transitive (
    const BinaryRelation & LESS,
    const BinaryRelation & NLESS,
    Ob x,
    Ob y,
    DenseSet & z_set)
{
    z_set.set_insn(NLESS.get_Lx_set(x), LESS.get_Lx_set(y));
    if (unlikely(not z_set.empty())) {
        return true;
    }

    z_set.set_insn(LESS.get_Rx_set(x), NLESS.get_Rx_set(y));
    if (unlikely(not z_set.empty())) {
        return true;
    }

    return false;
}

// NLESS fun x z fun y z   NLESS fun z x fun z y
// ---------------------   ---------------------
//       NLESS x y               NLESS x y
inline bool infer_nless_monotone (
    const BinaryRelation & NLESS,
    const BinaryFunction & fun,
    const DenseSet & nonconst,
    Ob x,
    Ob y,
    DenseSet & z_set)
{
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

// TODO infer associativity
//
// ----------------------------------
// EQUAL APP COMP x y z APP x APP y z
//
// -------------------------------------
// EQUAL JOIN JOIN x y z JOIN x JOIN y z
//
// -------------------------------------
// EQUAL RAND RAND x y z RAND x RAND y z

} // anonymous namespace

// ---------------------   ----------------------------
// EQUAL APP APP K x y x   EQUAL COMP APP K x y APP K x
size_t infer_const (Structure & structure)
{
    POMAGMA_INFO("Inferring K");

    const Carrier & carrier = structure.carrier();
    const NullaryFunction & K = structure.nullary_function("K");
    BinaryFunction & APP = structure.binary_function("APP");
    BinaryFunction & COMP = structure.binary_function("COMP");

    DenseSet y_set(carrier.item_dim());

    size_t theorem_count = 0;
    if (Ob K_ = K.find()) {
        for (auto iter = APP.iter_lhs(K_); iter.ok(); iter.next()) {
            Ob x = * iter;
            Ob APP_K_x = APP.find(K_, x);

            y_set.set_diff(carrier.support(), APP.get_Lx_set(APP_K_x));
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                Ob y = * iter;
                APP.insert(APP_K_x, y, x);
                ++theorem_count;
            }

            y_set.set_diff(carrier.support(), COMP.get_Lx_set(APP_K_x));
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                Ob y = * iter;
                COMP.insert(APP_K_x, y, APP_K_x);
                ++theorem_count;
            }
        }
    }

    POMAGMA_INFO("inferred " << theorem_count << " K facts");
    return theorem_count;
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
    const size_t item_dim = carrier.item_dim();

    size_t start_count = NLESS.count_pairs();

    std::mutex mutex;
    #pragma omp parallel
    {
        DenseSet y_set(item_dim);
        DenseSet z_set(item_dim);
        LhsFixedTheoremQueue theorems(NLESS);

        #pragma omp for schedule(dynamic, 1)
        for (Ob x = 1; x <= item_dim; ++x) {
            if (not carrier.contains(x)) { continue; }

            y_set.set_pnn(
                carrier.support(),
                LESS.get_Lx_set(x),
                NLESS.get_Lx_set(x));
            for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
                Ob y = * iter;
                POMAGMA_ASSERT(carrier.contains(y), "unsupported ob: " << y);
                POMAGMA_ASSERT_UNDECIDED(LESS, x, y);
                POMAGMA_ASSERT_UNDECIDED(NLESS, x, y);

                if (infer_nless_transitive(LESS, NLESS, x, y, z_set) or
                    infer_nless_monotone(NLESS, APP, nonconst, x, y, z_set) or
                    infer_nless_monotone(NLESS, COMP, nonconst, x, y, z_set))
                {
                    theorems.push(x, y);
                }
            }

            theorems.flush(mutex);
        }
    }

    size_t theorem_count = NLESS.count_pairs() - start_count;
    POMAGMA_INFO("inferred " << theorem_count << " NLESS facts");
    return theorem_count;
}

size_t infer_less (Structure & structure)
{
    POMAGMA_INFO("Inferring LESS");

    Signature & signature = structure.signature();
    const Carrier & carrier = structure.carrier();
    BinaryRelation & LESS = structure.binary_relation("LESS");
    const BinaryRelation & NLESS = structure.binary_relation("NLESS");
    const BinaryFunction & APP = structure.binary_function("APP");
    const BinaryFunction & COMP = structure.binary_function("COMP");
    const SymmetricFunction * JOIN = signature.symmetric_functions("JOIN");
    const SymmetricFunction * RAND = signature.symmetric_functions("RAND");
    const DenseSet nonconst = get_nonconst(structure);

    size_t start_count = LESS.count_pairs();

    infer_less_transitive(carrier, LESS, NLESS);
    infer_less_monotone(LESS, APP, nonconst);
    infer_less_monotone(LESS, COMP, nonconst);
    if (JOIN) {
        infer_less_convex(carrier, LESS, * JOIN);
    }
    if (RAND) {
        infer_less_linear(carrier, LESS, * RAND);
    }

    size_t theorem_count = LESS.count_pairs() - start_count;
    POMAGMA_INFO("inferred " << theorem_count << " LESS facts");
    return theorem_count;
}

size_t infer_equal (Structure & structure)
{
    POMAGMA_INFO("Inferring EQUAL");

    Carrier & carrier = structure.carrier();
    const BinaryRelation & LESS = structure.binary_relation("LESS");

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

    size_t theorem_count = carrier.item_dim() - carrier.item_count();
    POMAGMA_INFO("inferred " << theorem_count << " EQUAL facts");
    return theorem_count;
}

size_t infer_pos (Structure & structure)
{
    size_t theorem_count = 0;
    theorem_count += infer_const(structure);
    theorem_count += infer_less(structure);
    theorem_count += infer_equal(structure);
    return theorem_count;
}

size_t infer_neg (Structure & structure)
{
    size_t theorem_count = 0;
    theorem_count += infer_nless(structure);
    return theorem_count;
}

} // namespace pomagma
