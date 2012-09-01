#ifndef POMAGMA_BINARY_RELATION_HPP
#define POMAGMA_BINARY_RELATION_HPP

#include "util.hpp"
#include "dense_set.hpp"
#include "base_bin_rel.hpp"

namespace pomagma
{

// WARNING zero/null items are not allowed

// a pair of dense sets of dense sets, one col-row, one row-col
class BinaryRelation : noncopyable
{
    struct Pos
    {
        Ob lhs;
        Ob rhs;
        Pos (Ob l = 0, Ob r = 0) : lhs(l), rhs(r) {}
        bool operator == (const Pos & p) const
        {
            return lhs == p.lhs and rhs == p.rhs;
        }
        bool operator != (const Pos & p) const
        {
            return lhs != p.lhs or rhs != p.rhs;
        }
    };

    // data
    base_bin_rel m_lines;

    size_t item_dim () const { return m_lines.item_dim(); }
    size_t word_dim () const { return m_lines.word_dim(); }
    size_t round_item_dim () const { return m_lines.round_item_dim(); }
    size_t round_word_dim () const { return m_lines.round_word_dim(); }
    size_t data_size_words () const { return m_lines.data_size_words(); }

public:

    // set wrappers
    DenseSet get_Lx_set (Ob lhs) const { return m_lines.Lx_set(lhs); }
    DenseSet get_Rx_set (Ob rhs) const { return m_lines.Rx_set(rhs); }

    // ctors & dtors
    BinaryRelation (const Carrier & carrier);
    ~BinaryRelation ();
    void move_from (const BinaryRelation & other, const Ob* new2old=NULL);

    // attributes
    const DenseSet & support () const { return m_lines.support(); }
    size_t count_pairs () const; // supa-slow, try not to use
    void validate () const;
    void validate_disjoint (const BinaryRelation & other) const;
    void print_table (size_t n = 0) const;

    // element operations
    bool contains_Lx (Ob i, Ob j) const { return m_lines.Lx(i, j); }
    bool contains_Rx (Ob i, Ob j) const { return m_lines.Rx(i, j); }
    bool contains (Ob i, Ob j) const { return contains_Lx(i, j); }
    bool operator() (Ob i, Ob j) const { return contains(i, j); }
    bool contains (const Pos & p) const { return contains_Lx(p); }
    bool contains_Lx (const Pos & p) const
    {
        return contains_Lx(p.lhs, p.rhs);
    }
    bool contains_Rx (const Pos & p) const
    {
        return contains_Rx(p.lhs, p.rhs);
    }
private:
    // one-sided versions
    void insert_Lx (Ob i, Ob j) { m_lines.Lx(i, j).one(); }
    void insert_Rx (Ob i, Ob j) { m_lines.Rx(i, j).one(); }
    void remove_Lx (Ob i, Ob j) { m_lines.Lx(i, j).zero(); }
    void remove_Rx (Ob i, Ob j) { m_lines.Rx(i, j).zero(); }
    void remove_Lx (const DenseSet & is, Ob i);
    void remove_Rx (Ob i, const DenseSet & js);
public:
    // two-sided versions
    void insert (Ob i, Ob j) { insert_Lx(i, j); insert_Rx(i, j); }
    void remove (Ob i, Ob j) { remove_Lx(i, j); remove_Rx(i, j); }
    // these return whether there was a change
    inline bool ensure_inserted_Lx (Ob i, Ob j);
    inline bool ensure_inserted_Rx (Ob i, Ob j);
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
};

//----------------------------------------------------------------------------
// Operations

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

//----------------------------------------------------------------------------
// Iteration, always LR

class BinaryRelation::iterator : noncopyable
{
    DenseSet::Iter m_lhs;
    DenseSet::Iter m_rhs;
    DenseSet m_rhs_set;
    const BinaryRelation & m_rel;
    Pos m_pos;

public:

    // construction
    iterator (const BinaryRelation * rel)
        : m_lhs(rel->support(), false),
          m_rhs(m_rhs_set, false),
          m_rhs_set(rel->item_dim(), NULL),
          m_rel(*rel)
    {
        begin();
    }

    // traversal
private:
    void _update_lhs () { m_pos.lhs = *m_lhs; }
    void _update_rhs () { m_pos.rhs = *m_rhs; }
    void _finish () { m_pos.lhs = m_pos.rhs = 0; }
    void _find_rhs (); // finds first rhs, possibly incrementing lhs
public:
    void begin () { m_lhs.begin(); _find_rhs(); }
    void next ()
    {
        m_rhs.next();
        if (m_rhs.ok()) {
            _update_rhs();
        } else {
            m_lhs.next();
            _find_rhs();
        }
    }
    bool ok () const { return m_lhs.ok(); }

    // dereferencing
private:
    void _deref_assert () const
    {
        POMAGMA_ASSERT5(ok(), "dereferenced done br::iterator");
    }
public:
    const Pos & operator *  () const { _deref_assert(); return m_pos; }
    const Pos * operator -> () const { _deref_assert(); return &m_pos; }

    // access
    Ob lhs () const { return m_pos.lhs; }
    Ob rhs () const { return m_pos.rhs; }
};

//----------------------------------------------------------------------------
// Iteration over a line, LR or RL

enum Direction { LHS_FIXED=true, RHS_FIXED=false };
template<bool dir>
class BinaryRelation::Iterator : noncopyable
{
protected:
    DenseSet m_moving_set;
    DenseSet::Iter m_moving;
    Ob m_fixed;
    Pos m_pos;
    const BinaryRelation & m_rel;

public:

    // construction
    Iterator (Ob fixed, const BinaryRelation * rel)
        : m_moving_set(rel->item_dim(), dir ? rel->m_lines.Lx(fixed)
                                            : rel->m_lines.Rx(fixed)),
          m_moving(m_moving_set, false),
          m_fixed(fixed),
          m_rel(*rel)
    {
        POMAGMA_ASSERT2(m_rel.supports(fixed),
                "br::Iterator's fixed pos is unsupported");
        begin();
    }
    Iterator (const BinaryRelation * rel)
        : m_moving_set(rel->item_dim(), NULL),
          m_moving(m_moving_set, false),
          m_fixed(0),
          m_rel(*rel)
    {}

    // traversal
private:
    void _fix  () { (dir ? m_pos.lhs : m_pos.rhs) = m_fixed; }
    void _move () { (dir ? m_pos.rhs : m_pos.lhs) = *m_moving; }
public:
    void begin ()
    {
        POMAGMA_ASSERT(m_fixed, "tried to begin() a null br::Iterator");
        m_moving.begin();
        if (m_moving.ok()) { _fix(); _move(); }
    }
    void begin (Ob fixed)
    {   POMAGMA_ASSERT2(m_rel.supports(fixed),
                "br::Iterator's fixed pos is unsupported");
        m_fixed = fixed;
        m_moving_set.init(dir ? m_rel.m_lines.Lx(fixed)
                              : m_rel.m_lines.Rx(fixed));
        begin();
    }
    void next ()
    {
        m_moving.next();
        if (m_moving.ok()) { _move(); }
    }
    bool ok () const { return m_moving.ok(); }

    // dereferencing
private:
    void _deref_assert () const
    {
        POMAGMA_ASSERT5(ok(), "dereferenced done BinaryRelation'n::iter");
    }
public:
    const Pos & operator *  () const { _deref_assert(); return m_pos; }
    const Pos * operator -> () const { _deref_assert(); return &m_pos; }

    // access
    Ob fixed () const { return m_fixed; }
    Ob moving () const { return * m_moving; }
    Ob lhs () const { return m_pos.lhs; }
    Ob rhs () const { return m_pos.rhs; }
};

} // namespace pomagma

#endif // POMAGMA_BINARY_RELATION_HPP
