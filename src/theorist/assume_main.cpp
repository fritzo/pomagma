#include <pomagma/macrostructure/carrier.hpp>
#include <pomagma/macrostructure/structure.hpp>
#include "assume.hpp"

int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    const char * source_file = nullptr;
    const char * destin_file = nullptr;
    const char * theory_file = nullptr;

    if (argc == 4) {
        source_file = argv[1];
        destin_file = argv[2];
        theory_file = argv[3];
        POMAGMA_ASSERT_NE(std::string(source_file), std::string(destin_file));
    } else {
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

    // load structure
    pomagma::Structure structure;
    structure.load(source_file);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        structure.validate();
    }

    // assume
    int pre_item_count = structure.carrier().item_count();
    pomagma::assume(structure, theory_file);
    int post_item_count = structure.carrier().item_count();
    int merge_count = pre_item_count - post_item_count;
    POMAGMA_INFO("assumption merged " << merge_count << " obs");
    if (POMAGMA_DEBUG_LEVEL > 1) {
        structure.validate();
    }

    structure.dump(destin_file);

    // TODO
    //pomagma::log_stats();

    return 0;
}
