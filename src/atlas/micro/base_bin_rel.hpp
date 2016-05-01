#pragma once

#include "util.hpp"
#include "carrier.hpp"
#include <pomagma/util/concurrent/dense_set.hpp>

namespace pomagma {

template <bool symmetric>
class base_bin_rel_ : noncopyable {
    const Carrier &m_carrier;
    const size_t m_round_item_dim;
    const size_t m_round_word_dim;
    const size_t m_data_size_words;
    std::atomic<Word> *const m_Lx_lines;
    std::atomic<Word> *const m_Rx_lines;

   public:
    base_bin_rel_(const Carrier &carrier);
    ~base_bin_rel_();
    void validate() const;
    void log_stats(const std::string &prefix) const;

    const Carrier &carrier() const { return m_carrier; }
    const DenseSet &support() const { return m_carrier.support(); }
    size_t item_dim() const { return support().item_dim(); }
    size_t word_dim() const { return support().word_dim(); }
    size_t round_item_dim() const { return m_round_item_dim; }
    size_t round_word_dim() const { return m_round_word_dim; }
    size_t data_size_words() const { return m_data_size_words; }
    size_t count_pairs() const;  // supa-slow, try not to use
    void clear();
    void copy_Lx_to_Rx();

    // full table
    const std::atomic<Word> *Lx() const { return m_Lx_lines; }
    const std::atomic<Word> *Rx() const { return m_Rx_lines; }
    std::atomic<Word> *Lx() { return m_Lx_lines; }
    std::atomic<Word> *Rx() { return m_Rx_lines; }

    // single line
    const std::atomic<Word> *Lx(Ob lhs) const {
        POMAGMA_ASSERT_RANGE_(5, lhs, item_dim());
        return m_Lx_lines + (lhs * m_round_word_dim);
    }
    const std::atomic<Word> *Rx(Ob rhs) const {
        POMAGMA_ASSERT_RANGE_(5, rhs, item_dim());
        return m_Rx_lines + (rhs * m_round_word_dim);
    }
    std::atomic<Word> *Lx(Ob lhs) {
        POMAGMA_ASSERT_RANGE_(5, lhs, item_dim());
        return m_Lx_lines + (lhs * m_round_word_dim);
    }
    std::atomic<Word> *Rx(Ob rhs) {
        POMAGMA_ASSERT_RANGE_(5, rhs, item_dim());
        return m_Rx_lines + (rhs * m_round_word_dim);
    }

    // single element
    bool Lx(Ob lhs, Ob rhs) const {
        POMAGMA_ASSERT_RANGE_(5, rhs, item_dim());
        return bool_ref::index(Lx(lhs), rhs);
    }
    bool Rx(Ob lhs, Ob rhs) const {
        POMAGMA_ASSERT_RANGE_(5, lhs, item_dim());
        return bool_ref::index(Rx(rhs), lhs);
    }
    bool_ref Lx(Ob lhs, Ob rhs) {
        POMAGMA_ASSERT_RANGE_(5, rhs, item_dim());
        return bool_ref::index(Lx(lhs), rhs);
    }
    bool_ref Rx(Ob lhs, Ob rhs) {
        POMAGMA_ASSERT_RANGE_(5, lhs, item_dim());
        return bool_ref::index(Rx(rhs), lhs);
    }
    bool get_Lx(Ob lhs, Ob rhs) const { return Lx(lhs, rhs); }
    bool get_Rx(Ob lhs, Ob rhs) const { return Rx(lhs, rhs); }

    // set wrappers
    DenseSet Lx_set(Ob lhs) const {
        return DenseSet(item_dim(), const_cast<std::atomic<Word> *>(Lx(lhs)));
    }
    DenseSet Rx_set(Ob rhs) const {
        return DenseSet(item_dim(), const_cast<std::atomic<Word> *>(Rx(rhs)));
    }
};

typedef base_bin_rel_<false> base_bin_rel;
typedef base_bin_rel_<true> base_sym_rel;

}  // namespace pomagma
