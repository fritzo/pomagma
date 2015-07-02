#include "consistency.hpp"
#include <pomagma/atlas/world/scheduler.hpp>
#include <pomagma/atlas/world/carrier.hpp>
#include <pomagma/atlas/world/binary_relation.hpp>
#include <unistd.h> // for _exit

namespace pomagma
{

namespace
{

Carrier * g_checker_carrier = nullptr;
BinaryRelation * g_checker_nless = nullptr;

void schedule_merge_if_consistent (Ob dep)
{
    Ob rep = g_checker_carrier->find(dep);
    POMAGMA_ASSERT_LT(rep, dep);
    if (g_checker_nless->find(dep, rep) or g_checker_nless->find(rep, dep)) {
        POMAGMA_INFO("INCONSISTENT");
        _exit(EXIT_INCONSISTENT);
    } else {
        schedule_merge(dep);
    }
}

} // anonymous namespace

void configure_scheduler_to_merge_if_consistent (
        Structure & structure)
{
    g_checker_carrier = & structure.carrier();
    g_checker_nless = & structure.binary_relation("NLESS");
    g_checker_carrier->set_merge_callback(schedule_merge_if_consistent);
}

} // namespace pomagma
