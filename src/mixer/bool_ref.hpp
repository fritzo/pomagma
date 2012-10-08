#pragma once

#include "util.hpp"
#include "threading.hpp"

namespace pomagma
{

class bool_ref
{
    std::atomic<Word> * const m_word;
    const Word m_mask;

public:

    bool_ref (std::atomic<Word> & word, size_t _i)
        : m_word(& word),
          m_mask(Word(1) << _i)
    {
        POMAGMA_ASSERT6(_i < BITS_PER_WORD, "out of range: " << _i);
    }
    static bool_ref index (std::atomic<Word> * line, size_t i)
    {
        return bool_ref(line[i >> WORD_POS_SHIFT], i & WORD_POS_MASK);
    }
    static bool index (
            const std::atomic<Word> * line,
            size_t i,
            order_t order = relaxed)
    {
        Word word = line[i >> WORD_POS_SHIFT].load(order);
        Word mask = Word(1) << (i & WORD_POS_MASK);
        return word & mask;
    }

    bool load (order_t order = relaxed) { return m_word->load(order) & m_mask; }
    void zero (order_t order = relaxed) { m_word->fetch_and(~m_mask, order); }
    void one (order_t order = relaxed) { m_word->fetch_or(m_mask, order); }
    bool fetch_one (order_t order = relaxed)
    {
        return m_word->fetch_or(m_mask, order) & m_mask;
    }
    bool fetch_zero (order_t order = relaxed)
    {
        return m_word->fetch_and(~m_mask, order) & m_mask;
    }
};

} // namespace pomagma
