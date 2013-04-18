#include "util.hpp"
#include "carrier.hpp"
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
DEF_EXECUTE(AssumeTask)

#undef DEF_EXECUTE

void load_structure (const std::string & filename)
{
    POMAGMA_INFO("loading structure from " << filename);
}

void dump_structure (const std::string & filename)
{
    POMAGMA_INFO("dumping structure to " << filename);
}

void load_vehicle (const std::string & filename)
{
    POMAGMA_INFO("loading vehicle from " << filename);
}

void execute (const SampleTask &, rng_t &)
{
    POMAGMA_INFO("executing SampleTask");
}

void declare_signature ()
{
    POMAGMA_INFO("declare_signature()");
}

void insert_nullary_functions ()
{
    POMAGMA_INFO("insert_nullary_functions()");
}

void assume_core_facts (const char * theory_file)
{
    POMAGMA_INFO("assume_core_facts(" << theory_file << ")");
}

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

void validate_all ()
{
    POMAGMA_INFO("validate_all()");
}

void log_stats ()
{
    POMAGMA_INFO("log_stats()");
}

} // namespace pomagma
