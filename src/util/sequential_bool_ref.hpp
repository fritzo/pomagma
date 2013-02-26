#pragma once

#include <pomagma/util/util.hpp>

namespace pomagma
{

class bool_ref
{
    Word & m_word;
    const Word m_mask;

public:

    bool_ref (Word & word, size_t _i)
        : m_word(word),
          m_mask(Word(1) << _i)
    {
        POMAGMA_ASSERT6(_i < BITS_PER_WORD, "out of range: " << _i);
    }
    static bool_ref index (Word * line, size_t i)
    {
        return bool_ref(line[i >> WORD_POS_SHIFT], i & WORD_POS_MASK);
    }
    static bool index (const Word * line, size_t i)
    {
        Word word = line[i >> WORD_POS_SHIFT];
        Word mask = Word(1) << (i & WORD_POS_MASK);
        return word & mask;
    }

    bool load () const { return m_word & m_mask; }
    void operator |= (bool b) { m_word |= b * m_mask; }
    void operator &= (bool b) { m_word &= ~(!b * m_mask); }
    void zero () { m_word &= ~m_mask; }
    void one () { m_word |= m_mask; }
    bool fetch_zero () { bool result = load(); zero(); return result; }
    bool fetch_one () { bool result = load(); one(); return result; }
};

} // namespace pomagma
