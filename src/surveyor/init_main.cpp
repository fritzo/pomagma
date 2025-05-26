#include <pomagma/atlas/micro/scheduler.hpp>
#include <pomagma/atlas/micro/util.hpp>

#include "theory.hpp"

int main(int argc, char** argv) {
    pomagma::Log::Context log_context(argc, argv);
    const char* executable = *argv++;

    if (argc != 6) {
        std::cout << "Usage: "
                  << std::filesystem::path(executable).filename().string()
                  << "structure_out symbols facts programs language" << "\n"
                  << "Environment Variables:\n"
                  << "  POMAGMA_SIZE = " << pomagma::DEFAULT_ITEM_DIM << "\n"
                  << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE
                  << "\n"
                  << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL
                  << "\n";
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    const char* structure_out = *argv++;
    const char* symbols_file = *argv++;
    const char* facts_file = *argv++;
    const char* programs_file = *argv++;
    const char* language_file = *argv++;

    // set params
    pomagma::Scheduler::set_thread_count();
    pomagma::load_signature(symbols_file);
    pomagma::load_programs(programs_file);
    pomagma::load_language(language_file);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        pomagma::validate_all();
    }

    // initialize
    pomagma::Scheduler::initialize(facts_file);
    pomagma::log_profile_stats();
    if (POMAGMA_DEBUG_LEVEL > 1) {
        pomagma::validate_all();
    } else {
        pomagma::validate_consistent();
    }

    // survey
    pomagma::Scheduler::survey();
    pomagma::log_profile_stats();
    if (POMAGMA_DEBUG_LEVEL > 0) {
        pomagma::validate_all();
    } else {
        pomagma::validate_consistent();
    }

    pomagma::log_stats();
    pomagma::dump_structure(structure_out);

    return 0;
}
