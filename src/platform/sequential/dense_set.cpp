
#include <pomagma/platform/sequential/dense_set.hpp>
#include <pomagma/platform/aligned_alloc.hpp>
#include <cstring>

#define POMAGMA_DEBUG1(message)
//#define POMAGMA_DEBUG1(message) POMAGMA_DEBUG(message)

namespace pomagma
{
namespace sequential
{

typedef size_t Ob;

DenseSet::DenseSet (size_t item_dim)
    : m_item_dim(item_dim),
      m_word_dim(items_to_words(m_item_dim)),
      m_words(pomagma::alloc_blocks<Word>(m_word_dim)),
      m_alias(false)
{
    POMAGMA_DEBUG1("creating DenseSet with " << m_word_dim << " lines");

    bzero(m_words, sizeof(Word) * m_word_dim);
}

void DenseSet::operator= (const DenseSet & other)
{
    POMAGMA_DEBUG1("copying DenseSet");
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    memcpy(m_words, other.m_words, sizeof(Word) * m_word_dim);
}

template<class Ob>
void DenseSet::copy_from (const DenseSet & other, const Ob * new2old)
{
    POMAGMA_DEBUG1("copying DenseSet");

    size_t minM = min(m_word_dim, other.m_word_dim);
    if (new2old == nullptr) {
        // just copy
        memcpy(m_words, other.m_words, sizeof(Word) * minM);
    } else {
        // copy & reorder
        bzero(m_words, sizeof(Word) * m_word_dim);
        for (size_t n = 1; n <= m_item_dim; ++n) {
            if (other.contains(new2old[n])) insert(n);
        }
    }
}

template void DenseSet::copy_from<uint16_t> (
        const DenseSet &,
        const uint16_t *);
template void DenseSet::copy_from<uint32_t> (
        const DenseSet &,
        const uint32_t *);

//----------------------------------------------------------------------------
// Diagnostics

// not fast
bool DenseSet::empty () const
{
    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        if (m_words[m]) return false;
    }
    return true;
}

// supa-slow, try not to use
size_t DenseSet::count_items () const
{
    size_t result = 0;
    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        // WARNING only unsigned's work with >>
        static_assert(Word(1) >> 1 == 0, "bitshifting Word fails");
        for (Word word = m_words[m]; word; word >>= 1) {
            result += word & Word(1);
        }
    }
    return result;
}

void DenseSet::validate () const
{
    // make sure padding bits are zero
    POMAGMA_ASSERT(not (m_words[0] & 1),
            "dense set contains null item");

    // deal with partially-filled final block
    size_t end = (m_item_dim + 1) % BITS_PER_WORD;
    if (end == 0) return;
    POMAGMA_ASSERT(not (m_words[m_word_dim - 1] >> end),
            "dense set's end bits are used: "
            << m_words[m_word_dim - 1]);
}


//----------------------------------------------------------------------------
// Insertion

void DenseSet::insert_all ()
{
    // slow version
    // for (size_t i = 1; i <= m_item_dim; ++i) { insert(i); }

    // fast version
    for (size_t m = 0; m < m_word_dim; ++m) {
        m_words[m] = FULL_WORD;
    }

    // deal with partially-filled final block
    size_t end = (m_item_dim + 1) % BITS_PER_WORD;
    if (end) {
        Word word = FULL_WORD >> (BITS_PER_WORD - end);
        m_words[m_word_dim - 1] = word;
    }

    m_words[0] ^= 1; // remove zero element
}

size_t DenseSet::insert_one ()
{
    m_words[0] ^= 1; // simplifies code

    Word * restrict word = assume_aligned(m_words);
    while (likely(! ~ * word)) {
        ++word;
    }
    size_t ob = BITS_PER_WORD * (word - m_words);

    const Word free = ~ * word;
    Word mask = 1;
    while (not (mask & free)) {
        mask <<= Word(1);
        ++ob;
    }
    * word |= mask;

    m_words[0] ^= 1; // simplifies code
    return ob;
}

//----------------------------------------------------------------------------
// Entire operations

void DenseSet::zero ()
{
    bzero(m_words, sizeof(Word) * m_word_dim);
}

inline void DenseSet::ensure_padding_bits_are_zero ()
{
    Word ones = ~ Word(0);
    m_words[0] &= ones << 1;
    size_t end = (m_item_dim + 1) % BITS_PER_WORD;
    if (end == 0) return;
    size_t padding = BITS_PER_WORD - end;
    m_words[m_word_dim - 1] &= ones >> padding;
}

bool DenseSet::operator== (const DenseSet & other) const
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    const Word * restrict s = assume_aligned(m_words);
    const Word * restrict t = assume_aligned(other.m_words);
    Word u = 0;

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        u |= s[m] ^ t[m];
    }

    return not u;
}

bool DenseSet::operator<= (const DenseSet & other) const
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    const Word * restrict s = assume_aligned(m_words);
    const Word * restrict t = assume_aligned(other.m_words);
    Word u = 0;

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        u |= s[m] & ~ t[m];
    }

    return not u;
}

bool DenseSet::disjoint (const DenseSet & other) const
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    const Word * restrict s = assume_aligned(m_words);
    const Word * restrict t = assume_aligned(other.m_words);
    Word u = 0;

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        u |= s[m] & t[m];
    }

    return not u;
}

// inplace union
void DenseSet::operator += (const DenseSet & other)
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    const Word * restrict s = assume_aligned(other.m_words);
    Word * restrict t = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        t[m] |= s[m];
    }
}

// inplace intersection
void DenseSet::operator *= (const DenseSet & other)
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    const Word * restrict s = assume_aligned(other.m_words);
    Word * restrict t = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        t[m] &= s[m];
    }
}

// inplace difference
void DenseSet::operator -= (const DenseSet & other)
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    const Word * restrict s = assume_aligned(other.m_words);
    Word * restrict t = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        t[m] &= ~ s[m];
    }
}

void DenseSet::set_union (const DenseSet & lhs, const DenseSet & rhs)
{
    POMAGMA_ASSERT1(item_dim() == lhs.item_dim(), "lhs.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == rhs.item_dim(), "rhs.item_dim mismatch");

    const Word * restrict s = assume_aligned(lhs.m_words);
    const Word * restrict t = assume_aligned(rhs.m_words);
    Word * restrict u = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        u[m] = s[m] | t[m];
    }
}

void DenseSet::set_insn (const DenseSet & lhs, const DenseSet & rhs)
{
    POMAGMA_ASSERT1(item_dim() == lhs.item_dim(), "lhs.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == rhs.item_dim(), "rhs.item_dim mismatch");

    const Word * restrict s = assume_aligned(lhs.m_words);
    const Word * restrict t = assume_aligned(rhs.m_words);
    Word * restrict u = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        u[m] = s[m] & t[m];
    }
}

void DenseSet::set_insn (
        const DenseSet & xs,
        const DenseSet & ys,
        const DenseSet & zs)
{
    POMAGMA_ASSERT1(item_dim() == xs.item_dim(), "xs.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == ys.item_dim(), "ys.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == zs.item_dim(), "zs.item_dim mismatch");

    const Word * restrict x = assume_aligned(xs.m_words);
    const Word * restrict y = assume_aligned(ys.m_words);
    const Word * restrict z = assume_aligned(zs.m_words);
    Word * restrict w = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        w[m] = x[m] & y[m] & z[m];
    }
}

void DenseSet::set_diff (const DenseSet & pos, const DenseSet & neg)
{
    POMAGMA_ASSERT1(item_dim() == pos.item_dim(), "pos.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == neg.item_dim(), "neg.item_dim mismatch");

    const Word * restrict s = assume_aligned(pos.m_words);
    const Word * restrict t = assume_aligned(neg.m_words);
    Word * restrict u = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        u[m] = s[m] & ~ t[m];
    }
}

void DenseSet::set_ppn (
    const DenseSet & pos1,
    const DenseSet & pos2,
    const DenseSet & neg)
{
    POMAGMA_ASSERT1(item_dim() == pos1.item_dim(), "pos1.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == pos2.item_dim(), "pos2.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == neg.item_dim(), "neg.item_dim mismatch");

    const Word * restrict s = assume_aligned(pos1.m_words);
    const Word * restrict t = assume_aligned(pos2.m_words);
    const Word * restrict u = assume_aligned(neg.m_words);
    Word * restrict v = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        v[m] = s[m] & t[m] & ~ u[m];
    }
}

void DenseSet::set_ppnn (
    const DenseSet & pos1,
    const DenseSet & pos2,
    const DenseSet & neg1,
    const DenseSet & neg2)
{
    POMAGMA_ASSERT1(item_dim() == pos1.item_dim(), "pos1.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == pos2.item_dim(), "pos2.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == neg1.item_dim(), "neg1.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == neg2.item_dim(), "neg2.item_dim mismatch");

    const Word * restrict s = assume_aligned(pos1.m_words);
    const Word * restrict t = assume_aligned(pos2.m_words);
    const Word * restrict u = assume_aligned(neg1.m_words);
    const Word * restrict v = assume_aligned(neg2.m_words);
    Word * restrict w = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        w[m] = s[m] & t[m] & ~ (u[m] | v[m]);
    }
}

void DenseSet::set_pnn (
    const DenseSet & pos,
    const DenseSet & neg1,
    const DenseSet & neg2)
{
    POMAGMA_ASSERT1(item_dim() == pos.item_dim(), "pos.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == neg1.item_dim(), "neg1.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == neg2.item_dim(), "neg2.item_dim mismatch");

    const Word * restrict s = assume_aligned(pos.m_words);
    const Word * restrict t = assume_aligned(neg1.m_words);
    const Word * restrict u = assume_aligned(neg2.m_words);
    Word * restrict v = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        v[m] = s[m] & ~ (t[m] | u[m]);
    }
}

// this += dep; dep = 0;
void DenseSet::merge (DenseSet & dep)
{
    POMAGMA_ASSERT4(m_item_dim == dep.m_item_dim, "dep has wrong size");

    Word * restrict d = assume_aligned(dep.m_words);
    Word * restrict r = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        r[m] |= d[m];
        d[m] = 0;
    }
}

// diff = dep - this; this += dep; dep = 0; return diff not empty;
bool DenseSet::merge (DenseSet & dep, DenseSet & diff)
{
    POMAGMA_ASSERT4(m_item_dim == dep.m_item_dim, "dep has wrong size");
    POMAGMA_ASSERT4(m_item_dim == diff.m_item_dim, "diff has wrong size");

    Word * restrict d = assume_aligned(dep.m_words);
    Word * restrict r = assume_aligned(m_words);
    Word * restrict c = assume_aligned(diff.m_words);

    Word changed = 0;
    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        Word dm = d[m];
        Word rm = r[m];
        Word change = dm & ~ rm;
        d[m] = 0;
        r[m] |= dm;
        c[m] = change;
        changed |= change;
    }

    return changed;
}

// diff = src - this; this += src; return diff not empty;
bool DenseSet::ensure (const DenseSet & src, DenseSet & diff)
{
    POMAGMA_ASSERT4(m_item_dim == src.m_item_dim, "src has wrong size");
    POMAGMA_ASSERT4(m_item_dim == diff.m_item_dim, "diff has wrong size");

    const Word * restrict d = assume_aligned(src.m_words);
    Word * restrict r = assume_aligned(m_words);
    Word * restrict c = assume_aligned(diff.m_words);

    Word changed = 0;
    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        Word dm = d[m];
        Word rm = r[m];
        Word change = dm & ~ rm;
        r[m] |= dm;
        c[m] = change;
        changed |= change;
    }

    return changed;
}

} // namespace sequential
} // namespace pomagma
