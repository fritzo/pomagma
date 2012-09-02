#include "binary_relation.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

namespace { void noop_callback (Ob, Ob) {} }

BinaryRelation::BinaryRelation (
        const Carrier & carrier,
        void (*insert_callback) (Ob, Ob))
    : m_lines(carrier),
      m_insert_callback(insert_callback ? insert_callback : noop_callback)
{
    POMAGMA_DEBUG("creating BinaryRelation with "
            << round_word_dim() << " words");
}

BinaryRelation::~BinaryRelation ()
{
}

void BinaryRelation::move_from (
        const BinaryRelation & other,
        const Ob * new2old)
{
    POMAGMA_DEBUG("Copying BinaryRelation");

    if (POMAGMA_DEBUG_LEVEL >= 1) other.validate();

    // WARNING: assumes this has been done
    //bzero(m_lines.Lx(), sizeof(Word) * data_size_words());
    //bzero(m_lines.Rx(), sizeof(Word) * data_size_words());

    if (new2old == NULL) {
        POMAGMA_DEBUG("copying by column and by row");
        m_lines.move_from(other.m_lines);
    } else {
        POMAGMA_DEBUG("copying and reordering");
        // copy & reorder WIKKIT SLOW
        for (Ob i_new = 1; i_new <= item_dim(); ++i_new) {
            if (not supports(i_new)) continue;
            Ob i_old = new2old[i_new];

            for (Ob j_new = 1; j_new <= item_dim(); ++j_new) {
                if (not supports(j_new)) continue;
                Ob j_old = new2old[j_new];

                if (other.find(i_old, j_old)) _insert(i_new, j_new);
            }
        }
    }
    if (POMAGMA_DEBUG_LEVEL >= 1) validate();
}

void BinaryRelation::validate () const
{
    UniqueLock lock(m_mutex);

    POMAGMA_DEBUG("Validating BinaryRelation");

    m_lines.validate();

    size_t num_pairs = 0;

    DenseSet Lx(round_item_dim(), NULL);
    DenseSet Rx(round_item_dim(), NULL);
    for (Ob i = 1; i <= item_dim(); ++i) {
        bool sup_i = supports(i);
        Lx.init(m_lines.Lx(i));

        for (Ob j = 1; j <= item_dim(); ++j) {
            bool sup_ij = sup_i and supports(j);
            Rx.init(m_lines.Rx(j));

            bool Lx_ij = Lx.contains(j);
            bool Rx_ij = Rx.contains(i);
            num_pairs += Rx_ij;

            POMAGMA_ASSERT(Lx_ij == Rx_ij,
                    "Lx,Rx disagree at " << i << "," << j
                    << ", Lx is " << Lx_ij << ", Rx is " << Rx_ij  );

            POMAGMA_ASSERT(sup_ij or not Lx_ij,
                    "Lx unsupported at " << i << "," << j );

            POMAGMA_ASSERT(sup_ij or not Rx_ij,
                    "Rx unsupported at " << i << "," << j );
        }
    }

    size_t true_size = count_pairs();
    POMAGMA_ASSERT(num_pairs == true_size,
            "incorrect number of pairs: "
            << num_pairs << " should be " << true_size);
}

void BinaryRelation::validate_disjoint (const BinaryRelation & other) const
{
    UniqueLock lock(m_mutex);

    POMAGMA_DEBUG("Validating disjoint pair of BinaryRelations");

    // validate supports agree
    POMAGMA_ASSERT_EQ(support().item_dim(), other.support().item_dim());
    POMAGMA_ASSERT_EQ(
            support().count_items(),
            other.support().count_items());
    POMAGMA_ASSERT(support() == other.support(),
            "BinaryRelation supports differ");

    // validate disjointness
    DenseSet this_set(item_dim(), NULL);
    DenseSet other_set(item_dim(), NULL);
    for (DenseSet::Iterator i(support()); i.ok(); i.next()) {
        this_set.init(m_lines.Lx(*i));
        other_set.init(other.m_lines.Lx(*i));
        POMAGMA_ASSERT(this_set.disjoint(other_set),
                "BinaryRelations intersect at row " << *i);
    }
}

// supa-slow, try not to use
size_t BinaryRelation::count_pairs () const
{
    size_t result = 0;
    for (DenseSet::Iterator i(support()); i.ok(); i.next()) {
        result += get_Lx_set(*i).count_items();
    }
    return result;
}

void BinaryRelation::insert (Ob i, const DenseSet & js)
{
    DenseSet diff(item_dim());
    DenseSet dest(item_dim(), m_lines.Lx(i));
    if (dest.ensure(js, diff)) {
        for (DenseSet::Iterator k(diff); k.ok(); k.next()) {
            _insert_Rx(i, *k);
            m_insert_callback(i, *k);
        }
    }
}

void BinaryRelation::insert (const DenseSet & is, Ob j)
{
    DenseSet diff(item_dim());
    DenseSet dest(item_dim(), m_lines.Rx(j));
    if (dest.ensure(is, diff)) {
        for (DenseSet::Iterator k(diff); k.ok(); k.next()) {
            _insert_Lx(*k, j);
            m_insert_callback(*k, j);
        }
    }
}

void BinaryRelation::_remove_Lx (const DenseSet & is, Ob j)
{
    // slower version
    //for (DenseSet::Iterator i(is); i.ok(); i.next()) {
    //    _remove_Lx(*i, j);
    //}

    // faster version
    Word mask = ~(Word(1) << (j % BITS_PER_WORD));
    size_t offset = j / BITS_PER_WORD;
    Word * lines = m_lines.Lx() + offset;
    for (DenseSet::Iterator i(is); i.ok(); i.next()) {
         lines[*i * round_word_dim()] &= mask; // ATOMIC
    }
}

void BinaryRelation::_remove_Rx (Ob i, const DenseSet& js)
{
    // slower version
    //for (DenseSet::Iterator j(js); j.ok(); j.next()) {
    //    _remove_Rx(i, *j);
    //}

    // faster version
    Word mask = ~(Word(1) << (i % BITS_PER_WORD));
    size_t offset = i / BITS_PER_WORD;
    Word * lines = m_lines.Rx() + offset;
    for (DenseSet::Iterator j(js); j.ok(); j.next()) {
         lines[*j * round_word_dim()] &= mask; // ATOMIC
    }
}

void BinaryRelation::remove (Ob ob)
{
    UniqueLock lock(m_mutex);

    DenseSet set(item_dim(), NULL);

    // remove column
    set.init(m_lines.Lx(ob));
    _remove_Rx(ob, set);
    set.zero();

    // remove row
    set.init(m_lines.Rx(ob));
    _remove_Lx(set, ob);
    set.zero();
}

// policy: callback whenever i~k but not j~k
void BinaryRelation::merge (Ob i, Ob j)
{
    UniqueLock lock(m_mutex);

    POMAGMA_ASSERT4(j != i, "BinaryRelation tried to merge item with self");

    DenseSet diff(item_dim());
    DenseSet rep(item_dim(), NULL);
    DenseSet dep(item_dim(), NULL);

    // merge rows (i, _) into (j, _)
    dep.init(m_lines.Lx(i));
    _remove_Rx(i, dep);
    rep.init(m_lines.Lx(j));
    if (rep.merge(dep, diff)) {
        for (DenseSet::Iterator k(diff); k.ok(); k.next()) {
            _insert_Rx(j, *k);
            m_insert_callback(j, *k);
        }
    }

    // merge cols (_, i) into (_, j)
    dep.init(m_lines.Rx(i));
    _remove_Lx(dep, i);
    rep.init(m_lines.Rx(j));
    if (rep.merge(dep, diff)) {
        for (DenseSet::Iterator k(diff); k.ok(); k.next()) {
            _insert_Lx(*k, j);
            m_insert_callback(*k, j);
        }
    }
}

} // namespace pomagma
