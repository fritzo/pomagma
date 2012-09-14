
#include "dense_set.hpp"
#include "aligned_alloc.hpp"
#include <cstring>

namespace pomagma
{

DenseSet::DenseSet (size_t item_dim)
    : m_item_dim(item_dim),
      m_word_dim(items_to_words(m_item_dim)),
      m_words(pomagma::alloc_blocks<std::atomic<Word>>(m_word_dim)),
      m_alias(false)
{
    POMAGMA_DEBUG("creating DenseSet with " << m_word_dim << " lines");
    POMAGMA_ASSERT_LE(item_dim, MAX_ITEM_DIM);

    bzero(m_words, sizeof(std::atomic<Word>) * m_word_dim);
}

void DenseSet::copy_from (const DenseSet & other, const Ob * new2old)
{
    POMAGMA_DEBUG("Copying DenseSet");

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

//----------------------------------------------------------------------------
// Diagnostics

// not fast
bool DenseSet::empty () const
{
    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        if (m_words[m].load(relaxed)) return false;
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
        for (Word word = m_words[m].load(relaxed); word; word >>= 1) {
            result += word & Word(1);
        }
    }
    return result;
}

void DenseSet::validate () const
{
    // make sure padding bits are zero
    POMAGMA_ASSERT(not (m_words[0].load(relaxed) & 1),
            "dense set contains null item");

    // deal with partially-filled final block
    size_t end = (m_item_dim + 1) % BITS_PER_WORD;
    if (end == 0) return;
    POMAGMA_ASSERT(not (m_words[m_word_dim - 1].load(relaxed) >> end),
            "dense set's end bits are used: "
            << m_words[m_word_dim - 1].load(relaxed));
}


//----------------------------------------------------------------------------
// Insertion

void DenseSet::insert_all ()
{
    // slow version
    // for (size_t i = 1; i <= m_item_dim; ++i) { insert(i); }

    // fast version
    for (size_t m = 0; m < m_word_dim; ++m) {
        m_words[m].store(FULL_WORD, relaxed);
    }

    // deal with partially-filled final block
    size_t end = (m_item_dim + 1) % BITS_PER_WORD;
    if (end) {
        Word word = FULL_WORD >> (BITS_PER_WORD - end);
        m_words[m_word_dim - 1].store(word, relaxed);
    }

    m_words[0].fetch_xor(1, relaxed); // remove zero element
}

Ob DenseSet::insert_one () // WARNING not thread safe
{
    m_words[0].fetch_xor(1, relaxed); // simplifies code

    std::atomic<Word> * restrict word = assume_aligned(m_words);
    while (! ~ word->load(relaxed)) {
        ++word;
    }
    Ob ob = BITS_PER_WORD * (word - m_words);

    const Word free = ~ word->load(relaxed);
    Word mask = 1;
    while (not (mask & free)) {
        mask <<= Word(1);
        ++ob;
    }
    word->fetch_or(mask, relaxed);

    m_words[0].fetch_xor(1, relaxed); // simplifies code
    return ob;
}

//----------------------------------------------------------------------------
// Entire operations

void DenseSet::zero ()
{
    bzero(m_words, sizeof(Word) * m_word_dim);
}

bool DenseSet::operator== (const DenseSet & other) const
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        if (m_words[m].load(relaxed) != other.m_words[m].load(relaxed)) {
            return false;
        }
    }
    return true;
}

bool DenseSet::operator<= (const DenseSet & other) const
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        if (m_words[m].load(relaxed) & ~other.m_words[m].load(relaxed)) {
            return false;
        }
    }
    return true;
}

bool DenseSet::disjoint (const DenseSet & other) const
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        if (m_words[m].load(relaxed) & other.m_words[m].load(relaxed)) {
            return false;
        }
    }
    return true;
}

// inplace union
void DenseSet::operator += (const DenseSet & other)
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    const std::atomic<Word> * restrict s = assume_aligned(other.m_words);
    std::atomic<Word> * restrict t = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        t[m].fetch_or(s[m].load(relaxed), relaxed);
    }
}

// inplace intersection
void DenseSet::operator *= (const DenseSet & other)
{
    POMAGMA_ASSERT1(item_dim() == other.item_dim(), "item_dim mismatch");

    const std::atomic<Word> * restrict s = assume_aligned(other.m_words);
    std::atomic<Word> * restrict t = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        t[m].fetch_and(s[m].load(relaxed), relaxed);
    }
}

void DenseSet::set_union (const DenseSet & lhs, const DenseSet & rhs)
{
    POMAGMA_ASSERT1(item_dim() == lhs.item_dim(), "lhs.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == rhs.item_dim(), "rhs.item_dim mismatch");

    const std::atomic<Word> * restrict s = assume_aligned(lhs.m_words);
    const std::atomic<Word> * restrict t = assume_aligned(rhs.m_words);
    std::atomic<Word> * restrict u = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        u[m].store(s[m].load(relaxed) | t[m].load(relaxed), relaxed);
    }
}

void DenseSet::set_insn (const DenseSet & lhs, const DenseSet & rhs)
{
    POMAGMA_ASSERT1(item_dim() == lhs.item_dim(), "lhs.item_dim mismatch");
    POMAGMA_ASSERT1(item_dim() == rhs.item_dim(), "rhs.item_dim mismatch");

    const std::atomic<Word> * restrict s = assume_aligned(lhs.m_words);
    const std::atomic<Word> * restrict t = assume_aligned(rhs.m_words);
    std::atomic<Word> * restrict u = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        u[m].store(s[m].load(relaxed) & t[m].load(relaxed), relaxed);
    }
}

// this += dep; dep = 0;
void DenseSet::merge (DenseSet & dep)
{
    POMAGMA_ASSERT4(m_item_dim == dep.m_item_dim, "dep has wrong size");

    std::atomic<Word> * restrict d = assume_aligned(dep.m_words);
    std::atomic<Word> * restrict r = assume_aligned(m_words);

    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        r[m].fetch_or(d[m].load(relaxed), relaxed);
        d[m].store(0, relaxed);
    }
}

// diff = dep - this; this += dep; dep = 0; return diff not empty;
bool DenseSet::merge (DenseSet & dep, DenseSet & diff)
{
    POMAGMA_ASSERT4(m_item_dim == dep.m_item_dim, "dep has wrong size");
    POMAGMA_ASSERT4(m_item_dim == diff.m_item_dim, "diff has wrong size");

    std::atomic<Word> * restrict d = assume_aligned(dep.m_words);
    std::atomic<Word> * restrict r = assume_aligned(m_words);
    std::atomic<Word> * restrict c = assume_aligned(diff.m_words);

    Word changed = 0;
    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        Word dm = d[m].load(relaxed);
        Word rm = r[m].load(relaxed);
        Word change = dm & ~ rm;
        d[m].store(0, relaxed);
        r[m].fetch_or(dm, relaxed);
        c[m].store(change, relaxed);
        changed |= change;
    }

    return changed;
}

// diff = src - this; this += src; return diff not empty;
bool DenseSet::ensure (const DenseSet & src, DenseSet & diff)
{
    POMAGMA_ASSERT4(m_item_dim == src.m_item_dim, "src has wrong size");
    POMAGMA_ASSERT4(m_item_dim == diff.m_item_dim, "diff has wrong size");

    const std::atomic<Word> * restrict d = assume_aligned(src.m_words);
    std::atomic<Word> * restrict r = assume_aligned(m_words);
    std::atomic<Word> * restrict c = assume_aligned(diff.m_words);

    Word changed = 0;
    for (size_t m = 0, M = m_word_dim; m < M; ++m) {
        Word dm = d[m].load(relaxed);
        Word rm = r[m].load(relaxed);
        Word change = dm & ~ rm;
        r[m].fetch_or(dm, relaxed);
        c[m].store(change, relaxed);
        changed |= change;
    }

    return changed;
}

} // namespace pomagma
