#include "symmetric_function.hpp"
#include <pomagma/util/aligned_alloc.hpp>
#include <cstring>

namespace pomagma
{

SymmetricFunction::SymmetricFunction (Carrier & carrier)
    : m_lines(carrier)
{
    POMAGMA_DEBUG("creating SymmetricFunction");
}

void SymmetricFunction::validate () const
{
    POMAGMA_INFO("Validating SymmetricFunction");

    m_lines.validate();

    POMAGMA_DEBUG("validating line-value consistency");
    for (size_t i = 1; i <= item_dim(); ++i)
    for (size_t j = i; j <= item_dim(); ++j) {
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

void SymmetricFunction::log_stats () const
{
    m_lines.log_stats();
}

void SymmetricFunction::clear ()
{
    m_lines.clear();
    m_values.clear();
}

void SymmetricFunction::update_values () const
{
    for (auto & pair : m_values) {
        Ob & dep = pair.second;
        Ob rep = carrier().find(dep);
        if (rep != dep) {
            dep = rep;
        }
    }
}

void SymmetricFunction::unsafe_merge (const Ob dep)
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
        Ob val = dep_iter->second;
        auto rep_iter = m_values.find(std::make_pair(lhs, rep));
        if (rep_iter == m_values.end()) {
            m_values.insert(std::make_pair(std::make_pair(lhs, rep), val));
            m_lines.Lx(lhs, rep).one();
        } else {
            carrier().set_and_merge(rep_iter->second, val);
        }
        m_values.erase(dep_iter);
        m_lines.Lx(lhs, dep).zero();
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
        Ob val = dep_iter->second;
        auto rep_iter = m_values.find(std::make_pair(rep, rhs));
        if (rep_iter == m_values.end()) {
            m_values.insert(std::make_pair(std::make_pair(rep, rhs), val));
            m_lines.Rx(rep, rhs).one();
        } else {
            carrier().set_and_merge(rep_iter->second, val);
        }
        m_values.erase(dep_iter);
        m_lines.Rx(dep, rhs).zero();
    }
    {
        DenseSet dep_set(item_dim(), m_lines.Lx(dep));
        DenseSet rep_set(item_dim(), m_lines.Lx(rep));
        rep_set.merge(dep_set);
    }

    // values must be updated in batch by update_values
}

} // namespace pomagma
