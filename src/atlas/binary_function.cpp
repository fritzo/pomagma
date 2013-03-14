#include "binary_function.hpp"
#include <pomagma/util/aligned_alloc.hpp>
#include <cstring>

namespace pomagma
{

BinaryFunction::BinaryFunction (Carrier & carrier)
    : m_lines(carrier)
{
    POMAGMA_DEBUG("creating BinaryFunction");
}

void BinaryFunction::validate () const
{
    POMAGMA_INFO("Validating BinaryFunction");

    m_lines.validate();

    POMAGMA_DEBUG("validating line-value consistency");
    for (size_t i = 1; i <= item_dim(); ++i)
    for (size_t j = 1; j <= item_dim(); ++j) {
        auto val_iter = m_values.find(std::make_pair(i, j));

        if (not (support().contains(i) and support().contains(j))) {
            POMAGMA_ASSERT(val_iter == m_values.end(),
                    "found unsupported lhs, rhs: " << i << ',' << j);
        } else if (val_iter != m_values.end()) {
            POMAGMA_ASSERT(defined(i, j),
                    "found undefined value: " << i << ',' << j);
            Ob val = val_iter->second;
            POMAGMA_ASSERT(val, "found zero value: " << i << ',' << j);
            POMAGMA_ASSERT(support().contains(val),
                    "found unsupported value: " << i << ',' << j);
        } else {
            POMAGMA_ASSERT(not defined(i, j),
                    "found defined null value: " << i << ',' << j);
        }
    }
}

void BinaryFunction::log_stats () const
{
    m_lines.log_stats();
}

void BinaryFunction::clear ()
{
    m_lines.clear();
    m_values.clear();
}

void BinaryFunction::update_values () const
{
    for (auto & pair : m_values) {
        Ob & dep = pair.second;
        Ob rep = carrier().find(dep);
        if (rep != dep) {
            dep = rep;
        }
    }
}

void BinaryFunction::unsafe_merge (const Ob dep)
{
    POMAGMA_ASSERT5(support().contains(dep), "unsupported dep: " << dep);
    Ob rep = carrier().find(dep);
    POMAGMA_ASSERT5(support().contains(rep), "unsupported rep: " << rep);
    POMAGMA_ASSERT4(rep != dep, "self merge: " << dep << "," << rep);

    // Note: in some cases, triples may move multiple times, e.g.
    //   (dep, dep) --> (dep, rep) --> (rep, rep)

    // dep as rhs
    for (auto iter = iter_rhs(dep); iter.ok(); iter.next()) {
        Ob lhs = *iter;
        auto dep_iter = m_values.find(std::make_pair(lhs, dep));
        Ob dep_val = dep_iter->second;
        m_values.erase(dep_iter);
        m_lines.Lx(lhs, dep).zero();
        Ob & rep_val = m_values[std::make_pair(lhs, rep)];
        if (carrier().set_or_merge(rep_val, dep_val)) {
            m_lines.Lx(lhs, rep).one();
        }
    }
    {
        DenseSet dep_set(item_dim(), m_lines.Rx(dep));
        DenseSet rep_set(item_dim(), m_lines.Rx(rep));
        rep_set.merge(dep_set);
    }

    // dep as lhs
    rep = carrier().find(rep);
    for (auto iter = iter_lhs(dep); iter.ok(); iter.next()) {
        Ob rhs = *iter;
        auto dep_iter = m_values.find(std::make_pair(dep, rhs));
        Ob dep_val = dep_iter->second;
        m_values.erase(dep_iter);
        m_lines.Rx(dep, rhs).zero();
        Ob & rep_val = m_values[std::make_pair(rep, rhs)];
        if (carrier().set_or_merge(rep_val, dep_val)) {
            m_lines.Rx(rep, rhs).one();
        }
    }
    {
        DenseSet dep_set(item_dim(), m_lines.Lx(dep));
        DenseSet rep_set(item_dim(), m_lines.Lx(rep));
        rep_set.merge(dep_set);
    }

    // values must be updated in batch by update_values
}

} // namespace pomagma
