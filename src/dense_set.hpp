#ifndef POMAGMA_DENSE_SET_HPP
#define POMAGMA_DENSE_SET_HPP

#include "util.hpp"
//#include "aligned_alloc.hpp"

namespace pomagma
{

// WARNING zero/null items are not allowed

//----------------------------------------------------------------------------
// Dense set - basically a bitfield

class DenseSet
{
    // data
    const size_t m_item_dim;
    const size_t m_word_dim;
    Word * m_words;
    const bool m_alias;

public:

    // position 0 is unused, so we count from item 1
    static size_t word_count (size_t item_dim)
    {
        return (item_dim + BITS_PER_WORD) / BITS_PER_WORD;
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

    // ctors & dtors
    DenseSet (size_t item_dim);
    DenseSet (size_t item_dim, Word * line)
        : m_item_dim(item_dim),
          m_word_dim(word_count(item_dim)),
          m_words(line),
          m_alias(true)
    {
        POMAGMA_ASSERT_LE(item_dim, MAX_ITEM_DIM);
    }

    // return-by-value is allowed, but general copy is not
    DenseSet (const DenseSet & other)
        : m_item_dim(other.m_item_dim),
          m_word_dim(other.m_word_dim),
          m_words(other.m_words),
          m_alias(other.m_alias)
    {
        POMAGMA_ASSERT(m_alias, "copy-constructed a non-alias DenseSet");
    }
    DenseSet (const DenseSet & other, verify_copy_construction)
        : m_item_dim(other.m_item_dim),
          m_word_dim(other.m_word_dim),
          m_words(other.m_words),
          m_alias(true)
    {
    }
private:
    void operator= (const DenseSet & other); // intentionally undefined
public:
    //DenseSet (size_t item_dim, AlignedBuffer<Word> & buffer)
    //    : m_item_dim(item_dim),
    //      m_word_dim(word_count(item_dim)),
    //      m_words(buffer(m_word_dim)),
    //      m_alias(true)
    //{
    //}
    ~DenseSet ();
    void move_from (const DenseSet & other, const Ob * new2old = NULL);
    void init (Word * line)
    {
        POMAGMA_ASSERT4(m_alias, "tried to init() non-alias dense set");
        m_words = line;
    }

    // attributes
    bool empty () const; // not fast
    size_t count_items () const; // supa-slow, try not to use
    size_t item_dim () const { return m_item_dim; }
    size_t word_dim () const { return m_word_dim; }
    size_t data_size_bytes () const { return sizeof(Word) * m_word_dim; }
    void validate () const;

    // element operations
private:
    inline bool_ref _bit (size_t i);
    inline bool _bit (size_t i) const;
public:
    bool_ref operator() (size_t i) { return _bit(i); }
    bool operator() (size_t i) const { return _bit(i); }
    bool contains (size_t i) const { return _bit(i); }
    inline void insert (size_t i);
    inline void remove (size_t i);
    inline void merge  (size_t i, size_t j);
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

    // iteration
    class Iter;
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

//----------------------------------------------------------------------------
// Iteration

class DenseSet::Iter : noncopyable
{
    size_t m_i;
    size_t m_rem;
    size_t m_quot;
    Word m_mask;
    const DenseSet & m_set;

public:

    // construction
    Iter (const DenseSet & set, bool b = true)
        : m_set(set)
    {
        if (b) { begin(); }
    }

    // traversal
private:
    void _next_block ();
public:
    inline void begin ();
    void next ();
    bool ok () const { return m_i; }

    // dereferencing
    size_t operator * () const { POMAGMA_ASSERT_OK return m_i; }
    const size_t * operator -> () const { POMAGMA_ASSERT_OK return & m_i; }
};

inline void DenseSet::Iter::begin ()
{
    POMAGMA_ASSERT4(m_set.m_words, "begin with null set");
    m_quot = 0;
    --m_quot;
    _next_block();
    POMAGMA_ASSERT5(not ok() or m_set.contains(m_i),
            "begin on empty pos: " << m_i);
}

} // namespace pomagma

#endif // POMAGMA_DENSE_SET_HPP
