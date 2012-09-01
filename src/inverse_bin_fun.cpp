#include "inverse_bin_fun.hpp"

namespace pomagma
{

#define POMAGMA_ASSERT_CONTAINS(POMAGMA_set, POMAGMA_x, POMAGMA_y, POMAGMA_z)\
    POMAGMA_ASSERT(contains(POMAGMA_set, POMAGMA_x, POMAGMA_y, POMAGMA_z),\
    #POMAGMA_set " is missing " #POMAGMA_x ", " #POMAGMA_y ", " #POMAGMA_z)

void inverse_bin_fun::validate (BinaryFunction & fun)
{
    POMAGMA_INFO("Validating inverse_bin_fun");

    for (DenseSet::Iterator lhs_iter(fun.support());
        lhs_iter.ok();
        lhs_iter.next())
    {
        Ob lhs = *lhs_iter;
        DenseSet rhs_set = fun.get_Lx_set(lhs);
        for (DenseSet::Iterator rhs_iter(rhs_set);
            rhs_iter.ok();
            rhs_iter.next())
        {
            Ob rhs = *rhs_iter;
            Ob val = fun.find(lhs, rhs);

            POMAGMA_ASSERT_CONTAINS(m_Vlr_data, val, lhs, rhs);
            POMAGMA_ASSERT_CONTAINS(m_VLr_data, val, lhs, rhs);
            POMAGMA_ASSERT_CONTAINS(m_VRl_data, val, rhs, lhs);
        }
    }

    for (Ob val = 1; val <= item_dim(); ++val) {
        for (auto lr : m_Vlr_data[val]) {
            Ob lhs = lr.first;
            Ob rhs = lr.second;
            POMAGMA_ASSERT_EQ(fun.get_value(lhs, rhs), val);
        }
    }

    for (auto VL_iter : m_VLr_data) {
        Ob val = VL_iter.first.first;
        Ob lhs = VL_iter.first.second;
        for (Ob rhs : VL_iter.second) {
            POMAGMA_ASSERT_EQ(fun.get_value(lhs, rhs), val);
        }
    }

    for (auto VR_iter : m_VRl_data) {
        Ob val = VR_iter.first.first;
        Ob rhs = VR_iter.first.second;
        for (Ob lhs : VR_iter.second) {
            POMAGMA_ASSERT_EQ(fun.get_value(lhs, rhs), val);
        }
    }
}

} // namespace pomagma
