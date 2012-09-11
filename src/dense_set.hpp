#ifndef POMAGMA_DENSE_SET_HPP
#define POMAGMA_DENSE_SET_HPP

#include "util.hpp"
#include "bool_ref.hpp"

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

class DenseSetIterator
{
    const size_t m_word_dim;
    const Word * const m_words;
    size_t m_i;
    size_t m_rem;
    size_t m_quot;
    Word m_mask;

public:

    DenseSetIterator (size_t item_dim, const Word * words)
        : m_word_dim(items_to_words(item_dim)),
          m_words(words)
    {
        POMAGMA_ASSERT4(m_words, "constructed Iterator with null words");
        m_quot = 0;
        --m_quot;
        _next_block();
        POMAGMA_ASSERT5(not ok() or bool_ref::index(m_words, m_i),
                "begin on empty pos: " << m_i);
    }

    void next ();
    bool ok () const { return m_i; }

    size_t operator * () const { POMAGMA_ASSERT_OK return m_i; }

private:

    void _next_block ();
};

//----------------------------------------------------------------------------
// Dense set - basically a bitfield

class DenseSet : noncopyable
{
    const size_t m_item_dim;
    const size_t m_word_dim;
    Word * m_words;
    const bool m_alias;

public:

    DenseSet (size_t item_dim);
    DenseSet (size_t item_dim, Word * line)
        : m_item_dim(item_dim),
          m_word_dim(items_to_words(item_dim)),
          m_words(line),
          m_alias(true)
    {
        POMAGMA_ASSERT_LE(item_dim, MAX_ITEM_DIM);
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
    //DenseSet (size_t item_dim, AlignedBuffer<Word> & buffer)
    //    : m_item_dim(item_dim),
    //      m_word_dim(items_to_words(item_dim)),
    //      m_words(buffer(m_word_dim)),
    //      m_alias(true)
    //{
    //}
    ~DenseSet () { if (not m_alias and m_words) free_blocks(m_words); }
    void copy_from (const DenseSet & other, const Ob * new2old = nullptr);
    void init (Word * line)
    {
        POMAGMA_ASSERT4(m_alias, "tried to init() non-alias dense set");
        POMAGMA_ASSERT_ALIGNED_(1, line);
        m_words = line;
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
    void validate () const;

    // element operations
    bool_ref operator() (size_t i) { return _bit(i); }
    bool operator() (size_t i) const { return _bit(i); }
    bool contains (size_t i) const { return _bit(i); }
    void insert (size_t i);
    void remove (size_t i);
    void merge  (size_t i, size_t j);
    void insert_all ();
    Ob insert_one ();

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

    typedef DenseSetIterator Iterator;
    Iterator iter () const { return Iterator(m_item_dim, m_words); }

private:

    bool_ref _bit (size_t i);
    bool _bit (size_t i) const;
};

inline bool_ref DenseSet::_bit (size_t i)
{
    POMAGMA_ASSERT_RANGE_(5, i, m_item_dim);
    return bool_ref::index(m_words, i);
}
inline bool DenseSet::_bit (size_t i) const
{
    POMAGMA_ASSERT_RANGE_(5, i, m_item_dim);
    return bool_ref::index(m_words, i);
}

inline void DenseSet::insert (size_t i)
{
    POMAGMA_ASSERT4(not contains(i), "double insertion: " << i);
    _bit(i).one();
}

inline void DenseSet::remove (size_t i)
{
    POMAGMA_ASSERT4(contains(i), "double removal: " << i);
    _bit(i).zero();
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

} // namespace pomagma

#endif // POMAGMA_DENSE_SET_HPP
