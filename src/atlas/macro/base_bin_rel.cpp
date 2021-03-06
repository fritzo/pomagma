#include "base_bin_rel.hpp"
#include <pomagma/util/aligned_alloc.hpp>
#include <cstring>

namespace pomagma {

template <bool symmetric>
base_bin_rel_<symmetric>::base_bin_rel_(const Carrier &carrier)
    : m_carrier(carrier),
      m_round_item_dim(DenseSet::round_item_dim(item_dim())),
      m_round_word_dim(DenseSet::round_word_dim(item_dim())),
      m_data_size_words((1 + m_round_item_dim) * m_round_word_dim),
      m_Lx_lines(pomagma::alloc_blocks<Word>(m_data_size_words)),
      m_Rx_lines(symmetric ? m_Lx_lines
                           : pomagma::alloc_blocks<Word>(m_data_size_words)) {
    POMAGMA_DEBUG("creating base_bin_rel_ with " << m_data_size_words
                                                 << " words");
    POMAGMA_ASSERT(m_round_item_dim <= MAX_ITEM_DIM,
                   "base_bin_rel_ is too large");

    zero_blocks(m_Lx_lines, m_data_size_words);
    if (not symmetric) {
        zero_blocks(m_Rx_lines, m_data_size_words);
    }
}

template <bool symmetric>
base_bin_rel_<symmetric>::base_bin_rel_(const Carrier &carrier,
                                        base_bin_rel_<symmetric> &&other)
    : m_carrier(carrier),
      m_round_item_dim(DenseSet::round_item_dim(item_dim())),
      m_round_word_dim(DenseSet::round_word_dim(item_dim())),
      m_data_size_words((1 + m_round_item_dim) * m_round_word_dim),
      m_Lx_lines(pomagma::alloc_blocks<Word>(m_data_size_words)),
      m_Rx_lines(symmetric ? m_Lx_lines
                           : pomagma::alloc_blocks<Word>(m_data_size_words)) {
    POMAGMA_DEBUG("creating base_bin_rel_ with " << m_data_size_words
                                                 << " words");
    POMAGMA_ASSERT(m_round_item_dim <= MAX_ITEM_DIM,
                   "base_bin_rel_ is too large");

    const size_t copy_dim = std::min(item_dim(), other.item_dim());
    zero_blocks(m_Lx_lines, m_data_size_words);
    for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
        Ob ob = *iter;
        DenseSet(copy_dim, Lx(ob)) = DenseSet(copy_dim, other.Lx(ob));
    }
    if (not symmetric) {
        zero_blocks(m_Rx_lines, m_data_size_words);
        for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
            Ob ob = *iter;
            DenseSet(copy_dim, Rx(ob)) = DenseSet(copy_dim, other.Rx(ob));
        }
    }
}

template <bool symmetric>
base_bin_rel_<symmetric>::~base_bin_rel_() {
    pomagma::free_blocks(m_Lx_lines);
    if (not symmetric) {
        pomagma::free_blocks(m_Rx_lines);
    }
}

template <bool symmetric>
void base_bin_rel_<symmetric>::validate() const {
    support().validate();

    if (symmetric) {
        // check emptiness outside of support
        const DenseSet set(item_dim(), nullptr);
        const DenseSet round_set(m_round_item_dim, nullptr);
        for (Ob i = 0; i < m_round_item_dim; ++i) {
            if (1 <= i and i <= item_dim() and support().contains(i)) {
                set.init(Lx(i));
                set.validate();
                POMAGMA_ASSERT(set <= support(), "Lx(i) exceeds support");
            } else {
                round_set.init(m_Lx_lines + m_round_word_dim * i);
                round_set.validate();
                POMAGMA_ASSERT(round_set.empty(), "unsupported Lx("
                                                      << i << ") has "
                                                      << round_set.count_items()
                                                      << " items");
            }
        }

        // check for Lx/Rx agreement
        for (Ob i = 1; i <= item_dim(); ++i) {
            for (Ob j = i; j <= item_dim(); ++j) {
                POMAGMA_ASSERT(Lx(i, j) == Rx(i, j), "Lx, Rx disagree at "
                                                         << i << ',' << j);
            }
        }

    } else {
        // check emptiness outside of support
        DenseSet set(item_dim(), nullptr);
        DenseSet round_set(m_round_item_dim, nullptr);
        for (Ob i = 0; i < m_round_item_dim; ++i) {
            if (1 <= i and i <= item_dim() and support().contains(i)) {
                set.init(Lx(i));
                set.validate();
                POMAGMA_ASSERT(set <= support(), "Lx(i) exceeds support");
                set.init(Rx(i));
                set.validate();
                POMAGMA_ASSERT(set <= support(), "Rx(i) exceeds support");
            } else {
                round_set.init(m_Lx_lines + m_round_word_dim * i);
                round_set.validate();
                POMAGMA_ASSERT(round_set.empty(), "unsupported Lx("
                                                      << i << ") has "
                                                      << round_set.count_items()
                                                      << " items");
                round_set.init(m_Rx_lines + m_round_word_dim * i);
                round_set.validate();
                POMAGMA_ASSERT(round_set.empty(), "unsupported Rx("
                                                      << i << ") has "
                                                      << round_set.count_items()
                                                      << " items");
            }
        }

        // check for Lx/Rx agreement
        for (auto i = support().iter(); i.ok(); i.next()) {
            for (auto j = support().iter(); j.ok(); j.next()) {
                POMAGMA_ASSERT(Lx(*i, *j) == Rx(*i, *j),
                               "Lx, Rx disagree at " << *i << ',' << *j);
            }
        }
    }
}

template <bool symmetric>
void base_bin_rel_<symmetric>::log_stats(const std::string &prefix) const {
    size_t pair_count = count_pairs();
    size_t pair_capacity = item_dim() * item_dim();
    float density = 1.0f * pair_count / pair_capacity;
    POMAGMA_INFO(prefix << " " << pair_count << " / " << pair_capacity << " = "
                        << density << " full");
}

template <bool symmetric>
size_t base_bin_rel_<symmetric>::count_pairs() const {
    size_t result = 0;
    for (auto i = support().iter(); i.ok(); i.next()) {
        result += Lx_set(*i).count_items();
    }
    return result;
}

template <bool symmetric>
void base_bin_rel_<symmetric>::clear() {
    if (symmetric) {
        zero_blocks(m_Lx_lines, data_size_words());
    } else {
        zero_blocks(m_Lx_lines, data_size_words());
        zero_blocks(m_Rx_lines, data_size_words());
    }
}

template <bool symmetric>
void base_bin_rel_<symmetric>::copy_Lx_to_Rx() {
    if (symmetric) {
        return;
    }

    zero_blocks(m_Rx_lines, data_size_words());

    const size_t size_ = m_round_word_dim;
    const size_t _size = BITS_PER_WORD;
    const size_t size = item_dim();

    for (size_t i_ = 0; i_ < size_; ++i_)
        for (size_t j_ = 0; j_ < size_; ++j_) {
            for (size_t _i = 0; _i < _size; ++_i) {
                const size_t i = i_ * _size + _i;
                if (i > size) {
                    break;
                }
                if (i == 0) {
                    continue;
                }
                const Word &source = Lx(i)[j_];
                const Word destin_mask = Word(1) << _i;
                for (size_t _j = 0; _j < _size; ++_j) {
                    size_t j = j_ * _size + _j;
                    if (j > size) {
                        break;
                    }
                    if (j == 0) {
                        continue;
                    }
                    const Word source_mask = Word(1) << _j;
                    if (source_mask & source) {
                        Word &destin = Rx(j_ * _size + _j)[i_];
                        destin |= destin_mask;
                    }
                }
            }
        }
}

//----------------------------------------------------------------------------
// Explicit template instantiation

template base_bin_rel_<1>::base_bin_rel_(const Carrier &);
template base_bin_rel_<1>::base_bin_rel_(const Carrier &, base_bin_rel_<1> &&);
template base_bin_rel_<1>::~base_bin_rel_();
template void base_bin_rel_<1>::validate() const;
template void base_bin_rel_<1>::log_stats(const std::string &) const;
template size_t base_bin_rel_<1>::count_pairs() const;
template void base_bin_rel_<1>::clear();
template void base_bin_rel_<1>::copy_Lx_to_Rx();

template base_bin_rel_<0>::base_bin_rel_(const Carrier &);
template base_bin_rel_<0>::base_bin_rel_(const Carrier &, base_bin_rel_<0> &&);
template base_bin_rel_<0>::~base_bin_rel_();
template void base_bin_rel_<0>::validate() const;
template void base_bin_rel_<0>::log_stats(const std::string &) const;
template size_t base_bin_rel_<0>::count_pairs() const;
template void base_bin_rel_<0>::clear();
template void base_bin_rel_<0>::copy_Lx_to_Rx();

}  // namespace pomagma
