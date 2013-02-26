#pragma once

#include <pomagma/util/util.hpp>
#include <pomagma/util/concurrent_bool_ref.hpp>
#include <pomagma/util/threading.hpp>

namespace pomagma
{

void free_blocks (void *);

// position 0 is unused, so count from item 1
inline size_t items_to_words (size_t item_dim)
{
    return (item_dim + BITS_PER_WORD) / BITS_PER_WORD;
}

//----------------------------------------------------------------------------
// Iteration

class SimpleSet
{
    const size_t m_word_dim;
    const std::atomic<Word> * const m_words;

public:

    SimpleSet (size_t item_dim, const std::atomic<Word> * words)
        : m_word_dim(items_to_words(item_dim)),
          m_words(words)
    {
        POMAGMA_ASSERT4(m_words, "constructed SimpleSet with null words");
    }

    size_t word_dim () const { return m_word_dim; }
    bool get_bit (size_t pos) const { return bool_ref::index(m_words, pos); }
    Word get_word (size_t quot) const { return m_words[quot].load(relaxed); }
};

class Intersection2
{
    const size_t m_word_dim;
    const std::atomic<Word> * const m_words1;
    const std::atomic<Word> * const m_words2;

public:

    Intersection2 (
            size_t item_dim,
            const std::atomic<Word> * words1,
            const std::atomic<Word> * words2)
        : m_word_dim(items_to_words(item_dim)),
          m_words1(words1),
          m_words2(words2)
    {
        POMAGMA_ASSERT4(m_words1, "constructed Intersection2 with null words1");
        POMAGMA_ASSERT4(m_words2, "constructed Intersection2 with null words2");
    }

    size_t word_dim () const { return m_word_dim; }
    bool get_bit (size_t pos) const
    {
        Word mask = Word(1) << (pos & WORD_POS_MASK);
        return mask & get_word(pos >> WORD_POS_SHIFT);
    }
    Word get_word (size_t quot) const
    {
        return m_words1[quot].load(relaxed) & m_words2[quot].load(relaxed);
    }
};

class Intersection3
{
    const size_t m_word_dim;
    const std::atomic<Word> * const m_words1;
    const std::atomic<Word> * const m_words2;
    const std::atomic<Word> * const m_words3;

public:

    Intersection3 (
            size_t item_dim,
            const std::atomic<Word> * words1,
            const std::atomic<Word> * words2,
            const std::atomic<Word> * words3)
        : m_word_dim(items_to_words(item_dim)),
          m_words1(words1),
          m_words2(words2),
          m_words3(words3)
    {
        POMAGMA_ASSERT4(m_words1, "constructed Intersection3 with null words1");
        POMAGMA_ASSERT4(m_words2, "constructed Intersection3 with null words2");
        POMAGMA_ASSERT4(m_words3, "constructed Intersection3 with null words3");
    }

    size_t word_dim () const { return m_word_dim; }
    bool get_bit (size_t pos) const
    {
        Word mask = Word(1) << (pos & WORD_POS_MASK);
        return mask & get_word(pos >> WORD_POS_SHIFT);
    }
    Word get_word (size_t quot) const
    {
        return m_words1[quot].load(relaxed)
             & m_words2[quot].load(relaxed)
             & m_words3[quot].load(relaxed);
    }
};

template<class Set>
class SetIterator
{
    Set m_set;
    size_t m_i;
    size_t m_rem;
    size_t m_quot;
    Word m_word;

protected:

    SetIterator (const Set & set)
        : m_set(set)
    {
        m_quot = 0;
        --m_quot;
        _next_block();
        POMAGMA_ASSERT5(not ok() or m_set.get_bit(m_i),
                "begin on empty pos: " << m_i);
    }

public:

    void next ();
    bool ok () const { return m_i; }
    size_t operator * () const { POMAGMA_ASSERT_OK return m_i; }

private:

    void _next_block ();
};

template<class Set>
void SetIterator<Set>::_next_block ()
{
    // traverse to next nonempty block
    do {
        if (++m_quot == m_set.word_dim()) { m_i = 0; return; }
        m_word = m_set.get_word(m_quot);
        load_barrier();
    } while (!m_word);

    // traverse to first nonempty bit in a nonempty block
    for (m_rem = 0; !(m_word & 1); ++m_rem, m_word >>= 1) {
        POMAGMA_ASSERT4(m_rem != BITS_PER_WORD, "found no bits");
    }
    m_i = m_rem + BITS_PER_WORD * m_quot;
    POMAGMA_ASSERT5(m_set.get_bit(m_i), "landed on empty pos: " << m_i);
}

// PROFILE this is one of the slowest methods
template<class Set>
void SetIterator<Set>::next ()
{
    POMAGMA_ASSERT_OK
    do {
        ++m_rem;
        //if (m_rem < BITS_PER_WORD) m_word >>=1; // slow version
        if (m_rem & WORD_POS_MASK) m_word >>= 1;    // fast version
        else { _next_block(); return; }
    } while (!(m_word & 1));
    m_i = m_rem + BITS_PER_WORD * m_quot;
    POMAGMA_ASSERT5(m_set.get_bit(m_i), "landed on empty pos: " << m_i);
}

//----------------------------------------------------------------------------
// Dense set - basically a bitfield

class DenseSet : noncopyable
{
    const size_t m_item_dim;
    const size_t m_word_dim;
    std::atomic<Word> mutable * m_words;
    const bool m_alias;

public:

    DenseSet (size_t item_dim);
    DenseSet (size_t item_dim, std::atomic<Word> * line)
        : m_item_dim(item_dim),
          m_word_dim(items_to_words(item_dim)),
          m_words(line),
          m_alias(true)
    {
        POMAGMA_ASSERT_ALIGNED_(1, line);
    }
    DenseSet (const DenseSet & other) = delete;
    DenseSet (DenseSet && other)
        : m_item_dim(other.m_item_dim),
          m_word_dim(other.m_word_dim),
          m_words(other.m_words),
          m_alias(other.m_alias)
    {
        other.m_words = nullptr;
    }
    ~DenseSet () { if (not m_alias and m_words) free_blocks(m_words); }
    void operator= (const DenseSet & other);
    void init (std::atomic<Word> * line)
    {
        POMAGMA_ASSERT4(m_alias, "tried to init() non-alias dense set");
        POMAGMA_ASSERT_ALIGNED_(1, line);
        m_words = line;
    }
    void init (const std::atomic<Word> * line) const
    {
        POMAGMA_ASSERT4(m_alias, "tried to init() non-alias dense set");
        POMAGMA_ASSERT_ALIGNED_(1, line);
        m_words = const_cast<std::atomic<Word> *>(line);
    }

    // using round dimensions ensures cache alignenet and autovectorizability
    static size_t round_item_dim (size_t min_item_dim)
    {
        return (min_item_dim + BITS_PER_CACHE_LINE) / BITS_PER_CACHE_LINE
            * BITS_PER_CACHE_LINE - 1;
    }
    static size_t round_word_dim (size_t min_item_dim)
    {
        return (min_item_dim + BITS_PER_CACHE_LINE) / BITS_PER_CACHE_LINE
            * (BITS_PER_CACHE_LINE / BITS_PER_WORD);
    }

    // attributes
    bool empty () const; // not fast
    size_t count_items () const; // supa-slow, try not to use
    size_t item_dim () const { return m_item_dim; }
    size_t word_dim () const { return m_word_dim; }
    size_t data_size_bytes () const { return sizeof(Word) * m_word_dim; }
    std::atomic<Word> * raw_data () { return m_words; }
    const std::atomic<Word> * raw_data () const { return m_words; }
    void validate () const;

    // element operations
    bool_ref operator() (size_t i) { return _bit(i); }
    bool operator() (size_t i, order_t order = relaxed) const
    {
        return _bit(i, order);
    }
    bool contains (size_t i, order_t order = relaxed) const
    {
        return _bit(i, order);
    }
    void insert (size_t i, order_t order = relaxed);
    bool try_insert (size_t i);
    void remove (size_t i, order_t order = relaxed);
    void merge  (size_t i, size_t j);
    void insert_all ();
    size_t try_insert_one ();

    // entire operations (note that all are monotonic)
    void zero ();
    bool operator == (const DenseSet & other) const;
    bool operator <= (const DenseSet & other) const;
    bool disjoint    (const DenseSet & other) const;
    void operator += (const DenseSet & other);
    void operator *= (const DenseSet & other);
    void set_union   (const DenseSet & lhs, const DenseSet & rhs);
    void set_insn    (const DenseSet & lhs, const DenseSet & rhs);
    void merge       (DenseSet & dep);
    bool merge       (DenseSet & dep, DenseSet & diff);
    bool ensure      (const DenseSet & dep, DenseSet & diff);
    // returns true if anything in rep changes

    struct Iterator;
    struct Iterator2;
    struct Iterator3;
    Iterator iter () const;
    Iterator2 iter_insn (const DenseSet & other) const;
    Iterator3 iter_insn (const DenseSet & set2, const DenseSet & set3) const;

private:

    bool_ref _bit (size_t i);
    bool _bit (size_t i, order_t = relaxed) const;
};

inline bool_ref DenseSet::_bit (size_t i)
{
    POMAGMA_ASSERT_RANGE_(5, i, m_item_dim);
    return bool_ref::index(m_words, i);
}

inline bool DenseSet::_bit (size_t i, order_t order) const
{
    POMAGMA_ASSERT_RANGE_(5, i, m_item_dim);
    return bool_ref::index(m_words, i, order);
}

inline void DenseSet::insert (size_t i, order_t order)
{
    POMAGMA_ASSERT4(not contains(i, order), "double insertion: " << i);
    _bit(i).one(order);
}

inline bool DenseSet::try_insert (size_t i)
{
    return not _bit(i).fetch_one(relaxed);
}

inline void DenseSet::remove (size_t i, order_t order)
{
    POMAGMA_ASSERT4(contains(i), "double removal: " << i);
    _bit(i).zero(order);
}

inline void DenseSet::merge (size_t i, size_t j __attribute__((unused)))
{
    POMAGMA_ASSERT5(0 < i and i <= m_item_dim, "rep out of range: " << i);
    POMAGMA_ASSERT5(0 < j and j <= m_item_dim, "dep out of range: " << j);
    POMAGMA_ASSERT5(i != j, "merge with self: " << i);
    POMAGMA_ASSERT5(i > j, "merge wrong order: " << i << " > " << j);
    POMAGMA_ASSERT4(contains(i), "merge rep not contained: " << i);
    POMAGMA_ASSERT4(contains(j), "merge dep not contained: " << j);
    _bit(i).zero();
}

//----------------------------------------------------------------------------
// Iteration

struct DenseSet::Iterator : SetIterator<SimpleSet>
{
    Iterator (size_t item_dim, const std::atomic<Word> * words)
        : SetIterator<SimpleSet>(SimpleSet(item_dim, words))
    {
    }
};

struct DenseSet::Iterator2 : SetIterator<Intersection2>
{
    Iterator2 (
            size_t item_dim,
            const std::atomic<Word> * words1,
            const std::atomic<Word> * words2)
        : SetIterator<Intersection2>(Intersection2(item_dim, words1, words2))
    {
    }
};

struct DenseSet::Iterator3 : SetIterator<Intersection3>
{
    Iterator3 (
            size_t item_dim,
            const std::atomic<Word> * words1,
            const std::atomic<Word> * words2,
            const std::atomic<Word> * words3)
        : SetIterator<Intersection3>(
                Intersection3(item_dim, words1, words2, words3))
    {
    }
};

inline DenseSet::Iterator DenseSet::iter () const
{
    return Iterator(m_item_dim, m_words);
}

inline DenseSet::Iterator2 DenseSet::iter_insn (const DenseSet & other) const
{
    return Iterator2(m_item_dim, m_words, other.m_words);
}

inline DenseSet::Iterator3 DenseSet::iter_insn (
        const DenseSet & set2,
        const DenseSet & set3) const
{
    return Iterator3(m_item_dim, m_words, set2.m_words, set3.m_words);
}

} // namespace pomagma
