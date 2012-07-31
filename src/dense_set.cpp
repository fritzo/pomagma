
#include "dense_set.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

dense_set::dense_set (size_t item_dim)
    : m_item_dim(item_dim),
      m_word_dim(word_count(m_item_dim)),
      m_words(pomagma::alloc_blocks<Word>(m_word_dim)),
      m_alias(false)
{
    POMAGMA_DEBUG("creating dense_set with " << m_word_dim << " lines");
    POMAGMA_ASSERT_LE(item_dim, MAX_ITEM_DIM);

    bzero(m_words, sizeof(Word) * m_word_dim);
}

dense_set::~dense_set ()
{
  if (not m_alias) pomagma::free_blocks(m_words);
}

// intentionally undefined
//void dense_set::operator= (const dense_set & other)
//{
//    POMAGMA_ASSERT_EQ(m_item_dim, other.m_item_dim);
//    if (m_words != other.m_words) {
//        memcpy(m_words, other.m_words, sizeof(Word) * m_word_dim);
//    }
//}

void dense_set::move_from (const dense_set & other, const oid_t * new2old)
{
    POMAGMA_DEBUG("Copying dense_set");

    size_t minM = min(m_word_dim, other.m_word_dim);
    if (new2old == NULL) {
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

//----------------------------------------------------------------------------
// Diagnostics

// not fast
bool dense_set::empty () const
{
    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        if (m_words[m]) return false;
    }
    return true;
}

// supa-slow, try not to use
size_t dense_set::count_items () const
{
    size_t result = 0;
    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        // WARNING only unsigned's work with >>
        static_assert(Word(1) >> 1 == 0, "bitshifting Word fails");
        for (Word word = m_words[m]; word; word >>= 1) {
            result += word & 1U;
        }
    }
    return result;
}

void dense_set::validate () const
{
    // make sure padding bits are zero
    POMAGMA_ASSERT(not (m_words[0] & 1), "dense set contains null item");

    // deal with partially-filled final block
    size_t end = (m_item_dim + 1) % BITS_PER_WORD;
    if (end == 0) return;
    POMAGMA_ASSERT(not (m_words[m_word_dim - 1] >> end),
            "dense set's end bits are used: " << m_words[m_word_dim - 1]);
}


//----------------------------------------------------------------------------
// Insertion

void dense_set::insert_all ()
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
        m_words[m_word_dim - 1] = FULL_WORD >> (BITS_PER_WORD - end);
    }

    m_words[0] ^= 1; // remove zero element
}

oid_t dense_set::insert_one () // WARNING not thread safe
{
    m_words[0] ^= Word(1); // simplifies code

    Word * restrict word = m_words;
    while (! ~ * word) {
        ++word;
    }
    oid_t oid = BITS_PER_WORD * (word - m_words);

    const Word free = ~ * word;
    Word mask = 1;
    while (not (mask & free)) {
        mask <<= 1u;
        ++oid;
    }
    *word |= mask;

    m_words[0] ^= Word(1); // simplifies code
    return oid;
}

//----------------------------------------------------------------------------
// Entire operations

void dense_set::zero ()
{
    bzero(m_words, sizeof(Word) * m_word_dim);
}

bool dense_set::operator== (const dense_set & other) const
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        if (m_words[m] != other.m_words[m]) return false;
    }
    return true;
}

bool dense_set::operator<= (const dense_set & other) const
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        if (m_words[m] & ~other.m_words[m]) return false;
    }
    return true;
}

bool dense_set::disjoint (const dense_set & other) const
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        if (m_words[m] & other.m_words[m]) return false;
    }
    return true;
}

// inplace union
void dense_set::operator += (const dense_set & other)
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    const Word * restrict s = other.m_words;
    Word * restrict t = m_words;

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        t[m] |= s[m];
    }
}

// inplace intersection
void dense_set::operator *= (const dense_set & other)
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    const Word * restrict s = other.m_words;
    Word * restrict t = m_words;

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        t[m] &= s[m];
    }
}

void dense_set::set_union (const dense_set & lhs, const dense_set & rhs)
{
    POMAGMA_ASSERT1(item_dim() == lhs.item_dim(), "lhs.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == rhs.item_dim(), "rhs.item_dim mismatch");

    const Word * restrict s = lhs.m_words;
    const Word * restrict t = rhs.m_words;
    Word * restrict u = m_words;

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        u[m] = s[m] | t[m];
    }
}

void dense_set::set_insn (const dense_set & lhs, const dense_set & rhs)
{
    POMAGMA_ASSERT1(item_dim() == lhs.item_dim(), "lhs.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == rhs.item_dim(), "rhs.item_dim mismatch");

    const Word * restrict s = lhs.m_words;
    const Word * restrict t = rhs.m_words;
    Word * restrict u = m_words;

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        u[m] = s[m] & t[m];
    }
}

// this += dep; dep = 0;
void dense_set::merge (dense_set & dep)
{
    POMAGMA_ASSERT4(m_item_dim == dep.m_item_dim, "dep has wrong size");

    Word * restrict d = dep.m_words;
    Word * restrict r = m_words;

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        r[m] |= d[m];
        d[m] = 0;
    }
}

// diff = dep - this; this += dep; dep = 0; return diff not empty;
bool dense_set::merge (dense_set & dep, dense_set & diff)
{
    POMAGMA_ASSERT4(m_item_dim == dep.m_item_dim, "dep has wrong size");
    POMAGMA_ASSERT4(m_item_dim == diff.m_item_dim, "diff has wrong size");

    Word * restrict d = dep.m_words;
    Word * restrict r = m_words;
    Word * restrict c = diff.m_words;

    Word changed = 0;
    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        changed |= (c[m] = d[m] & ~r[m]);
        r[m] |= d[m];
        d[m] = 0;
    }

    return changed;
}

// diff = src - this; this += src; return diff not empty;
bool dense_set::ensure (const dense_set & src, dense_set & diff)
{
    POMAGMA_ASSERT4(m_item_dim == src.m_item_dim, "src has wrong size");
    POMAGMA_ASSERT4(m_item_dim == diff.m_item_dim, "diff has wrong size");

    const Word * restrict d = src.m_words;
    Word * restrict r = m_words;
    Word * restrict c = diff.m_words;

    Word changed = 0;
    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        changed |= (c[m] = d[m] & ~r[m]);
        r[m] |= d[m];
    }

    return changed;
}

//----------------------------------------------------------------------------
// Iteration

void dense_set::iterator::_next_block ()
{
    // traverse to next nonempty block
    const Word * lines = m_set.m_words;
    do { if (++m_quot == m_set.m_word_dim) { m_i = 0; return; }
    } while (!lines[m_quot]);

    // traverse to first nonempty bit in a nonempty block
    Word word = lines[m_quot];
    for (m_rem = 0, m_mask = 1; !(m_mask & word); ++m_rem, m_mask <<= 1) {
        POMAGMA_ASSERT4(m_rem != BITS_PER_WORD, "found no bits");
    }
    m_i = m_rem + BITS_PER_WORD * m_quot;
    POMAGMA_ASSERT5(m_set.contains(m_i), "landed on empty pos " << m_i);
}

// PROFILE this is one of the slowest methods
void dense_set::iterator::next ()
{
    POMAGMA_ASSERT_OK
    Word word = m_set.m_words[m_quot];
    do {
        ++m_rem;
        //if (m_rem < BITS_PER_WORD) m_mask <<=1; // slow version
        if (m_rem & WORD_POS_MASK) m_mask <<= 1;    // fast version
        else { _next_block(); return; }
    } while (!(m_mask & word));
    m_i = m_rem + BITS_PER_WORD * m_quot;
    POMAGMA_ASSERT5(m_set.contains(m_i), "landed on empty pos " << m_i);
}

} // namespace pomagma
