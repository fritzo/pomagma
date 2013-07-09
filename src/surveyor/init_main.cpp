#include <pomagma/microstructure/util.hpp>
#include <pomagma/microstructure/scheduler.hpp>

namespace pomagma
{

void dump_structure (const std::string & filename);
void load_language (const std::string & filename);
void declare_signature ();
void validate_consistent ();
void validate_all ();
void log_stats ();

} // namespace pomagma


int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    if (argc != 5) {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << "structure_out theory language threads" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_SIZE = " << pomagma::DEFAULT_ITEM_DIM << "\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    const char * structure_out = argv[1];
    const char * theory_file = argv[2];
    const char * language_file = argv[3];
    const size_t thread_count = atoi(argv[4]);

    // set params
    pomagma::Scheduler::set_thread_count(thread_count);
    pomagma::declare_signature();
    pomagma::load_language(language_file);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        pomagma::validate_all();
    }

    // initialize
    pomagma::Scheduler::initialize(theory_file);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        pomagma::validate_all();
    } else {
        pomagma::validate_consistent();
    }

    // survey
    pomagma::Scheduler::survey();
    if (POMAGMA_DEBUG_LEVEL > 0) {
        pomagma::validate_all();
    } else {
        pomagma::validate_consistent();
    }

    pomagma::log_stats();

    pomagma::dump_structure(structure_out);

    return 0;
}
