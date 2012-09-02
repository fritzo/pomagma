#ifndef POMAGMA_BINARY_RELATION_HPP
#define POMAGMA_BINARY_RELATION_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include "base_bin_rel.hpp"

namespace pomagma
{

// a pair of dense sets of dense sets, one col-row, one row-col
class BinaryRelation : noncopyable
{

    base_bin_rel m_lines;

public:

    BinaryRelation (const Carrier & carrier);
    ~BinaryRelation ();
    void move_from (const BinaryRelation & other, const Ob* new2old=NULL);
    void validate () const;
    void validate_disjoint (const BinaryRelation & other) const;

    // attributes
    const DenseSet & support () const { return m_lines.support(); }
    size_t count_pairs () const; // supa-slow, try not to use

    // safe operations
    DenseSet get_Lx_set (Ob lhs) const { return m_lines.Lx_set(lhs); }
    DenseSet get_Rx_set (Ob rhs) const { return m_lines.Rx_set(rhs); }

    // element operations
    bool contains_Lx (Ob i, Ob j) const { return m_lines.Lx(i, j); }
    bool contains_Rx (Ob i, Ob j) const { return m_lines.Rx(i, j); }
    bool contains (Ob i, Ob j) const { return contains_Lx(i, j); }
    bool operator() (Ob i, Ob j) const { return contains(i, j); }
    // two-sided versions
    void insert (Ob i, Ob j) { insert_Lx(i, j); insert_Rx(i, j); }
    void remove (Ob i, Ob j) { remove_Lx(i, j); remove_Rx(i, j); }
    // these return whether there was a change
    bool ensure_inserted_Lx (Ob i, Ob j);
    bool ensure_inserted_Rx (Ob i, Ob j);
    bool ensure_inserted (Ob i, Ob j) { return ensure_inserted_Lx(i, j); }
    void ensure_inserted (
            Ob i,
            const DenseSet & js,
            void (*change)(Ob, Ob));
    void ensure_inserted (
            const DenseSet & is,
            Ob j,
            void (*change)(Ob, Ob));

    // support operations
    bool supports (Ob i) const { return support().contains(i); }
    bool supports (Ob i, Ob j) const
    {
        return supports(i) and supports(j);
    }
    void remove (Ob i);
    void merge (Ob dep, Ob rep, void (*move_to)(Ob, Ob));

    // saving/loading of block data
    Ob data_size () const;
    void write_to_file (FILE* file);
    void read_from_file (FILE* file);

    // iteration
    class iterator;
    enum Direction { LHS_FIXED=true, RHS_FIXED=false };
    template<bool dir> class Iterator;

private:

    size_t item_dim () const { return m_lines.item_dim(); }
    size_t word_dim () const { return m_lines.word_dim(); }
    size_t round_item_dim () const { return m_lines.round_item_dim(); }
    size_t round_word_dim () const { return m_lines.round_word_dim(); }
    size_t data_size_words () const { return m_lines.data_size_words(); }

    void insert_Lx (Ob i, Ob j) { m_lines.Lx(i, j).one(); }
    void insert_Rx (Ob i, Ob j) { m_lines.Rx(i, j).one(); }
    void remove_Lx (Ob i, Ob j) { m_lines.Lx(i, j).zero(); }
    void remove_Rx (Ob i, Ob j) { m_lines.Rx(i, j).zero(); }
    void remove_Lx (const DenseSet & is, Ob i);
    void remove_Rx (Ob i, const DenseSet & js);
};

// returns whether there was a change
inline bool BinaryRelation::ensure_inserted_Lx (Ob i, Ob j)
{
    bool_ref contained = m_lines.Lx(i, j);
    if (contained) return false;
    contained.one();
    insert_Rx(i, j);
    return true;
}

// returns whether there was a change
inline bool BinaryRelation::ensure_inserted_Rx (Ob i, Ob j)
{
    bool_ref contained = m_lines.Rx(i, j);
    if (contained) return false;
    contained.one();
    insert_Lx(i, j);
    return true;
}

} // namespace pomagma

#endif // POMAGMA_BINARY_RELATION_HPP
