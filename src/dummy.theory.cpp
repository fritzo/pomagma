#include "util.hpp"
#include "scheduler.hpp"

namespace pomagma
{

#define DEF_EXECUTE(POMAGMA_name)\
    void execute (const POMAGMA_name &)\
    { POMAGMA_INFO("executing " #POMAGMA_name) }

DEF_EXECUTE(MergeTask)
DEF_EXECUTE(CleanupTask)
DEF_EXECUTE(PositiveOrderTask)
DEF_EXECUTE(NegativeOrderTask)
DEF_EXECUTE(NullaryFunctionTask)
DEF_EXECUTE(InjectiveFunctionTask)
DEF_EXECUTE(BinaryFunctionTask)
DEF_EXECUTE(SymmetricFunctionTask)

#undef DEF_EXECUTE

} // namespace pomagma
