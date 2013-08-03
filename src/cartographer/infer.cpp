#include "infer.hpp"
#include <pomagma/macrostructure/structure_impl.hpp>


namespace pomagma
{

size_t infer (Structure & structure)
{
    Carrier & carrier = structure.carrier();
    BinaryRelation & LESS = structure.binary_relation("LESS");
    BinaryRelation & NLESS = structure.binary_relation("NLESS");
    BinaryFunction & APP = structure.binary_function("APP");
    BinaryFunction & COMP = structure.binary_function("COMP");

    DenseSet y_set(carrier.item_dim());
    DenseSet z_set(carrier.item_dim());

    size_t decision_count = 0;
    for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
        Ob x = * iter;

        y_set.set_union(NLESS.get_Lx_set(x), LESS.get_Lx_set(x));
        y_set.complement();
        for (auto iter = y_set.iter(); iter.ok(); iter.next()) {
            Ob y = * iter;

            /*
            LESS x z   LESS z y
            -------------------
                 LESS x y
            */
            z_set.set_insn(LESS.get_Lx_set(x), LESS.get_Rx_set(y));
            if (not z_set.empty()) {
                LESS.insert(x, y);
                goto decided;
            }

            /*
            LESS z x   NLESS z y
            --------------------
                  NLESS x y
            */
            z_set.set_insn(LESS.get_Rx_set(x), NLESS.get_Rx_set(y));
            if (not z_set.empty()) {
                NLESS.insert(x, y);
                goto decided;
            }

            /*
            NLESS APP x z APP y z
            ---------------------
                  NLESS x y
            */
            z_set.set_insn(APP.get_Lx_set(x), APP.get_Lx_set(y));
            for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
                Ob z = * iter;
                Ob xz = APP.find(x, z);
                Ob yz = APP.find(y, z);
                if (NLESS.find(xz, yz)) {
                    NLESS.insert(x, y);
                    goto decided;
                }
            }

            /*
            NLESS APP z x APP z y
            ---------------------
                  NLESS x y
            */
            z_set.set_insn(APP.get_Rx_set(x), APP.get_Rx_set(y));
            for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
                Ob z = * iter;
                Ob zx = APP.find(z, x);
                Ob zy = APP.find(z, y);
                if (NLESS.find(zx, zy)) {
                    NLESS.insert(x, y);
                    goto decided;
                }
            }

            /*
            NLESS COMP x z COMP y z
            ---------------------
                  NLESS x y
            */
            z_set.set_insn(COMP.get_Lx_set(x), COMP.get_Lx_set(y));
            for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
                Ob z = * iter;
                Ob xz = COMP.find(x, z);
                Ob yz = COMP.find(y, z);
                if (NLESS.find(xz, yz)) {
                    NLESS.insert(x, y);
                    goto decided;
                }
            }

            /*
            NLESS COMP z x COMP z y
            ---------------------
                  NLESS x y
            */
            z_set.set_insn(COMP.get_Rx_set(x), COMP.get_Rx_set(y));
            for (auto iter = z_set.iter(); iter.ok(); iter.next()) {
                Ob z = * iter;
                Ob zx = COMP.find(z, x);
                Ob zy = COMP.find(z, y);
                if (NLESS.find(zx, zy)) {
                    NLESS.insert(x, y);
                    goto decided;
                }
            }

            decided: ++decision_count;
        }
    }

    return decision_count;
}

} // namespace pomagma
