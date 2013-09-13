#include "infer.hpp"
#include "signature.hpp"
#include <pomagma/macrostructure/carrier.hpp>
#include <pomagma/macrostructure/structure.hpp>
#include <pomagma/macrostructure/compact.hpp>

int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    if (argc != 3) {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << " structure_in structure_out"
                << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    const char * structure_in = argv[1];
    const char * structure_out = argv[2];

    // load
    pomagma::Structure structure;
    structure.load(structure_in);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        structure.validate();
    }

    // infer
    pomagma::infer_eager(structure);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        structure.validate();
    }

    // compact
    pomagma::compact(structure);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        structure.validate();
    } else {
        structure.validate_consistent();
    }

    structure.log_stats();
    structure.dump(structure_out);

    return 0;
}
