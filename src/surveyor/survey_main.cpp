#include <pomagma/microstructure/util.hpp>
#include <pomagma/microstructure/scheduler.hpp>
#include "cleanup.hpp"

namespace pomagma
{

void load_signature (const std::string & filename);
void load_structure (const std::string & filename);
void dump_structure (const std::string & filename);
void load_programs (const std::string & filename);
void load_language (const std::string & filename);
void validate_consistent ();
void validate_all ();
void log_stats ();

} // namespace pomagma


int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);
    const char * executable = *argv++;

    if (argc != 8) {
        std::cout
            << "Usage: "
                << pomagma::get_filename(executable)
                << " structure_in structure_out facts language threads" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_SIZE = " << pomagma::DEFAULT_ITEM_DIM << "\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    const char * structure_in = *argv++;
    const char * structure_out = *argv++;
    const char * signature_file = *argv++;
    const char * facts_file = *argv++;
    const char * programs_file = *argv++;
    const char * language_file = *argv++;
    const size_t thread_count = atoi(*argv++);

    // set params
    pomagma::Scheduler::set_thread_count(thread_count);
    pomagma::load_signature(signature_file);
    pomagma::load_programs(programs_file);
    pomagma::load_language(language_file);
    pomagma::load_structure(structure_in);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        pomagma::validate_all();
    }

    // initialize
    pomagma::Scheduler::initialize(facts_file);
    pomagma::CleanupProfiler::cleanup();
    if (POMAGMA_DEBUG_LEVEL > 1) {
        pomagma::validate_all();
    } else {
        pomagma::validate_consistent();
    }

    // survey
    pomagma::Scheduler::survey();
    pomagma::CleanupProfiler::cleanup();
    if (POMAGMA_DEBUG_LEVEL > 0) {
        pomagma::validate_all();
    } else {
        pomagma::validate_consistent();
    }

    pomagma::log_stats();
    pomagma::dump_structure(structure_out);

    return 0;
}
