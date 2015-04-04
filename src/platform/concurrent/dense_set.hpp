#pragma once

#include <array>
#include <pomagma/platform/util.hpp>
#include <pomagma/platform/concurrent/bool_ref.hpp>
#include <pomagma/platform/threading.hpp>

namespace pomagma
{

void free_blocks (void *);

namespace concurrent
{

// position 0 is unused, so count from item 1
inline size_t items_to_words (size_t item_dim)
{
    return (item_dim + BITS_PER_WORD) / BITS_PER_WORD;
}

//----------------------------------------------------------------------------
// Iteration

template<size_t rank>
class Intersection
{
    const size_t m_word_dim;
    const std::array<const std::atomic<Word> *, rank> m_words;

public:

    Intersection (
            size_t item_dim,
            std::array<const std::atomic<Word> *, rank> words)
        : m_word_dim(items_to_words(item_dim)),
          m_words(words)
    {
        static_assert(rank >= 2, "rank must be at least 2");
        POMAGMA_ASSERT3(words.size() == rank,
            "constructed Intersection with wrong number of arguments");
        for (size_t i = 0; i < rank; ++i) {
            POMAGMA_ASSERT4(m_words[i],
                "constructed Intersection with null words" << i);
        }
    }

    size_t word_dim () const { return m_word_dim; }
    bool get_bit (size_t pos) const
    {
        Word mask = Word(1) << (pos & WORD_POS_MASK);
        return mask & get_word(pos >> WORD_POS_SHIFT);
    }
    Word get_word (size_t quot) const
    {
        Word word = m_words[0][quot].load(relaxed);
        for (size_t i = 1; i < rank; ++i) {
            word &= m_words[i][quot].load(relaxed);
        }
        return word;
    }
};

template<>
class Intersection<1>
{
    const size_t m_word_dim;
    const std::atomic<Word> * const m_words;

public:

    Intersection (size_t item_dim, const std::atomic<Word> * words)
        : m_word_dim(items_to_words(item_dim)),
          m_words(words)
    {
        POMAGMA_ASSERT4(m_words, "constructed SimpleSet with null words");
    }

    size_t word_dim () const { return m_word_dim; }
    bool get_bit (size_t pos) const { return bool_ref::index(m_words, pos); }
    Word get_word (size_t quot) const { return m_words[quot].load(relaxed); }
};

template<size_t rank>
class SetIterator
{
    Intersection<rank> m_set;
    size_t m_i;
    size_t m_rem;
    size_t m_quot;
    Word m_word;

public:

    SetIterator (
            size_t item_dim,
            std::array<const std::atomic<Word> *, rank> words)
        : m_set(item_dim, words)
    {
        _init();
    }

    SetIterator (
            size_t item_dim,
            const std::atomic<Word> * words)
        : m_set(item_dim, words)
    {
        static_assert(rank == 1, "cannot initialize with singleton");
        _init();
    }

    void next ();
    bool ok () const { return m_i; }
    size_t operator * () const { POMAGMA_ASSERT_OK return m_i; }

private:

    void _init ();
    void _next_block ();
};

template<size_t rank>
void SetIterator<rank>::_init ()
{
    m_quot = 0;
    --m_quot;
    _next_block();
    POMAGMA_ASSERT5(not ok() or m_set.get_bit(m_i),
            "begin on empty pos: " << m_i);
}

template<size_t rank>
void SetIterator<rank>::_next_block ()
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
template<size_t rank>
void SetIterator<rank>::next ()
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

    // using round dimensions ensures cache alignment and autovectorizability
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

    typedef SetIterator<1> Iterator;
    typedef SetIterator<2> Iterator2;
    typedef SetIterator<3> Iterator3;
    typedef SetIterator<4> Iterator4;
    typedef SetIterator<5> Iterator5;
    typedef SetIterator<6> Iterator6;

    Iterator iter () const;
    Iterator2 iter_insn (const DenseSet & other) const;
    Iterator3 iter_insn (const DenseSet & set2, const DenseSet & set3) const;
    Iterator4 iter_insn (
            const DenseSet & set2,
            const DenseSet & set3,
            const DenseSet & set4) const;
    Iterator5 iter_insn (
            const DenseSet & set2,
            const DenseSet & set3,
            const DenseSet & set4,
            const DenseSet & set5) const;
    Iterator6 iter_insn (
            const DenseSet & set2,
            const DenseSet & set3,
            const DenseSet & set4,
            const DenseSet & set5,
            const DenseSet & set6) const;

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

inline DenseSet::Iterator DenseSet::iter () const
{
    return Iterator(m_item_dim, m_words);
}

inline DenseSet::Iterator2 DenseSet::iter_insn (const DenseSet & other) const
{
    return Iterator2(m_item_dim, {{m_words, other.m_words}});
}

inline DenseSet::Iterator3 DenseSet::iter_insn (
        const DenseSet & set2,
        const DenseSet & set3) const
{
    return Iterator3(m_item_dim, {{m_words, set2.m_words, set3.m_words}});
}

inline DenseSet::Iterator4 DenseSet::iter_insn (
        const DenseSet & set2,
        const DenseSet & set3,
        const DenseSet & set4) const
{
    return Iterator4(m_item_dim, {{
        m_words,
        set2.m_words,
        set3.m_words,
        set4.m_words
    }});
}

inline DenseSet::Iterator5 DenseSet::iter_insn (
        const DenseSet & set2,
        const DenseSet & set3,
        const DenseSet & set4,
        const DenseSet & set5) const
{
    return Iterator5(m_item_dim, {{
        m_words,
        set2.m_words,
        set3.m_words,
        set4.m_words,
        set5.m_words
    }});
}

inline DenseSet::Iterator6 DenseSet::iter_insn (
        const DenseSet & set2,
        const DenseSet & set3,
        const DenseSet & set4,
        const DenseSet & set5,
        const DenseSet & set6) const
{
    return Iterator6(m_item_dim, {{
        m_words,
        set2.m_words,
        set3.m_words,
        set4.m_words,
        set5.m_words,
        set6.m_words
    }});
}

} // namespace concurrent
} // namespace pomagma
