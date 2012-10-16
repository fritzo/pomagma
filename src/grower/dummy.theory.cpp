#include "util.hpp"
#include "scheduler.hpp"

namespace pomagma
{

#define DEF_EXECUTE(POMAGMA_name)\
    void execute (const POMAGMA_name &)\
    { POMAGMA_INFO("executing " #POMAGMA_name); }

DEF_EXECUTE(MergeTask)
DEF_EXECUTE(ExistsTask)
DEF_EXECUTE(PositiveOrderTask)
DEF_EXECUTE(NegativeOrderTask)
DEF_EXECUTE(NullaryFunctionTask)
DEF_EXECUTE(InjectiveFunctionTask)
DEF_EXECUTE(BinaryFunctionTask)
DEF_EXECUTE(SymmetricFunctionTask)
DEF_EXECUTE(CleanupTask)
DEF_EXECUTE(SampleTask)

#undef DEF_EXECUTE

void cleanup_tasks_push_all ()
{
    POMAGMA_INFO("cleanup_tasks_push_all()");
}

bool cleanup_tasks_try_pop (CleanupTask &)
{
    POMAGMA_INFO("cleanup_tasks_try_pop()");
    return false;
}

bool sample_tasks_try_pop (SampleTask &)
{
    POMAGMA_INFO("sample_tasks_try_pop()");
    return false;
}

} // namespace pomagma
