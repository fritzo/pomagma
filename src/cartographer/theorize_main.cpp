#include "util.hpp"
#include "carrier.hpp"
#include "structure.hpp"
#include "theorize.hpp"

int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    const char * structure_file = nullptr;
    const char * language_file = nullptr;
    const char * conjectures_file = nullptr;

    if (argc == 4) {
        structure_file = argv[1];
        language_file = argv[2];
        conjectures_file = argv[3];
    } else {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << " structure_in language_in conjectures_out" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    // load structure
    pomagma::Structure structure;
    structure.load(structure_file);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        structure.validate();
    }

    // load language
    const auto language = pomagma::load_language(language_file);

    // compute language weights
    const auto weights = pomagma::measure_weights(structure, language);
    const auto parses = pomagma::parse_all(structure, language);

    // theorize
    pomagma::theorize(structure, weights, parses, conjectures_file);

    return 0;
}
