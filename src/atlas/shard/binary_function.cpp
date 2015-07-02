#include "binary_function.hpp"
#include <pomagma/util/aligned_alloc.hpp>
#include <cstring>

namespace pomagma {
namespace shard {

BinaryFunction::BinaryFunction (Carrier & carrier)
    : m_carrier(carrier)
{
    POMAGMA_DEBUG("creating BinaryFunction");
}

BinaryFunction::BinaryFunction (
        Carrier & carrier,
        BinaryFunction && other)
    : m_lhs_rhs(std::move(other.m_lhs_rhs)),
      m_rhs_lhs(std::move(other.m_rhs_lhs)),
      m_val_lhs(std::move(other.m_val_lhs)),
      m_val_rhs(std::move(other.m_val_rhs)),
      m_carrier(carrier)
{
    POMAGMA_DEBUG("resizing BinaryFunction");
}

void BinaryFunction::validate () const
{
    POMAGMA_INFO("Validating BinaryFunction");

    for (auto r = m_rhs_lhs.begin(); r != m_rhs_lhs.end(); ++r) {
        Ob rhs = r->first;
        POMAGMA_ASSERT(support().contains(rhs), "unsupported rhs: " << rhs);
        for (auto l = r->second.begin(); l != r->second.end(); ++l) {
            Ob lhs = l->first;
            POMAGMA_ASSERT(support().contains(lhs), "unsupported lhs: " << lhs);
            Ob val = l->second;
            POMAGMA_ASSERT(support().contains(val), "unsupported val: " << val);
            auto i = m_lhs_rhs.find(lhs);
            POMAGMA_ASSERT(i != m_lhs_rhs.end(), "missing lhs: " << lhs);
            auto j = i->second.find(rhs);
            POMAGMA_ASSERT(j != i->second.end(), "missing rhs: " << rhs);
            POMAGMA_ASSERT_EQ(val, j->second);
        }
    }

    for (auto l = m_lhs_rhs.begin(); l != m_rhs_lhs.end(); ++l) {
        Ob lhs = l->first;
        POMAGMA_ASSERT(support().contains(lhs), "unsupported lhs: " << lhs);
        for (auto r = l->second.begin(); r != l->second.end(); ++r) {
            Ob rhs = r->first;
            POMAGMA_ASSERT(support().contains(rhs), "unsupported rhs: " << rhs);
            Ob val = r->second;
            POMAGMA_ASSERT(support().contains(val), "unsupported val: " << val);
            auto i = m_rhs_lhs.find(rhs);
            POMAGMA_ASSERT(i != m_rhs_lhs.end(), "missing rhs: " << rhs);
            auto j = i->second.find(lhs);
            POMAGMA_ASSERT(j != i->second.end(), "missing lhs: " << lhs);
            POMAGMA_ASSERT_EQ(val, j->second);
        }
    }
}

void BinaryFunction::clear ()
{
    m_lhs_rhs.clear();
    m_rhs_lhs.clear();
    m_val_lhs.clear();
    m_val_rhs.clear();
}

void BinaryFunction::merge (const Ob dep)
{
    POMAGMA_ASSERT5(support().contains(dep), "unsupported dep: " << dep);
    Ob rep = carrier().find(dep);
    POMAGMA_ASSERT5(support().contains(rep), "unsupported rep: " << rep);
    POMAGMA_ASSERT4(rep != dep, "self merge: " << dep << "," << rep);

    TODO("implement");
}

} // namespace shard
} // namespace pomagma
