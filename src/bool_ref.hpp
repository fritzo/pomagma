#ifndef POMAGMA_BOOL_REF_HPP
#define POMAGMA_BOOL_REF_HPP

#include "util.hpp"

namespace pomagma
{

class unsafe_bool_ref
{
    Word & m_word;
    const Word m_mask;

public:

    unsafe_bool_ref (Word & word, size_t _i)
        : m_word(word),
          m_mask(Word(1) << _i)
    {
        POMAGMA_ASSERT6(_i < BITS_PER_WORD, "out of range: " << _i);
    }
    static unsafe_bool_ref index (Word * line, size_t i)
    {
        return unsafe_bool_ref(line[i >> WORD_POS_SHIFT], i & WORD_POS_MASK);
    }

    operator bool () const { return m_word & m_mask; }
    void operator |= (bool b) { m_word |= b * m_mask; }
    void operator &= (bool b) { m_word &= ~(!b * m_mask); }
    void zero () { m_word &= ~m_mask; }
    void one () { m_word |= m_mask; }
    void invert () { m_word ^= m_mask; }
};

class atomic_bool_ref
{
    std::atomic<Word> * const m_word;
    const Word m_mask;

public:

    atomic_bool_ref (Word & word, size_t _i)
        : m_word(reinterpret_cast<std::atomic<Word> *>(& word)), // HACK
          m_mask(Word(1) << _i)
    {
        POMAGMA_ASSERT6(_i < BITS_PER_WORD, "out of range: " << _i);
    }
    static atomic_bool_ref index (Word * line, size_t i)
    {
        return atomic_bool_ref(line[i >> WORD_POS_SHIFT], i & WORD_POS_MASK);
    }

    operator bool () const { return m_word->load() & m_mask; }
    void operator |= (bool b) { m_word->fetch_or(b * m_mask); }
    void operator &= (bool b) { m_word->fetch_and(~(!b * m_mask)); }
    void zero () { m_word->fetch_and(~m_mask); }
    void one () { m_word->fetch_or(m_mask); }
    void invert () { m_word->fetch_xor(m_mask); }
};

typedef unsafe_bool_ref bool_ref;

} // namespace pomagma

#endif // POMAGMA_BOOL_REF_HPP
