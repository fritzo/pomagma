#include <pomagma/macrostructure/carrier.hpp>
#include <pomagma/macrostructure/structure.hpp>
#include "assume.hpp"

int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    if (argc != 4) {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << " structure destin theory" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    const char * source_file = argv[1];
    const char * destin_file = argv[2];
    const char * theory_file = argv[3];
    POMAGMA_ASSERT_NE(std::string(source_file), std::string(destin_file));

    // load structure
    pomagma::Structure structure;
    structure.load(source_file);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        structure.validate();
    }

    // assume
    pomagma::assume(structure, theory_file);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        structure.validate();
    }

    structure.log_stats();
    structure.dump(destin_file);

    return 0;
}
