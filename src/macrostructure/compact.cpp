#include "compact.hpp"
#include "carrier.hpp"
#include "scheduler.hpp"

namespace pomagma
{

void compact (Structure & structure)
{
    POMAGMA_INFO("Compacting structure");

    Carrier & carrier = structure.carrier();
    size_t item_count = carrier.item_count();
    POMAGMA_ASSERT_EQ(carrier.rep_count(), item_count);

    carrier.set_merge_callback(schedule_merge);
    for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
        Ob dep = * iter;
        if (dep > item_count) {
            Ob rep = carrier.unsafe_insert();
            POMAGMA_ASSERT_LE(rep, item_count);
            carrier.merge(dep, rep);
        }
    }
    POMAGMA_ASSERT_EQ(carrier.rep_count(), item_count);

    process_mergers(structure.signature());
    POMAGMA_ASSERT_EQ(carrier.item_count(), item_count);
}

} // namespace pomagma
