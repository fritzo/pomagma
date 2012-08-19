#include "util.hpp"
#include "task_manager.hpp"

namespace pomagma
{

#define DEF_EXECUTE(POMAGMA_name)\
    void execute (const POMAGMA_name &)\
    { POMAGMA_INFO("executing " #POMAGMA_name) }

DEF_EXECUTE(EquationTask)
DEF_EXECUTE(PositiveOrderTask)
DEF_EXECUTE(NegativeOrderTask)
DEF_EXECUTE(NullaryFunctionTask)
DEF_EXECUTE(UnaryFunctionTask)
DEF_EXECUTE(BinaryFunctionTask)
DEF_EXECUTE(SymmetricFunctionTask)

#undef DEF_EXECUTE

} // namespace pomagma
