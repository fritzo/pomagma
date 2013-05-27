#include "util.hpp"
#include "carrier.hpp"
#include "structure.hpp"
#include "conjecture.hpp"

int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    const char * structure_file = nullptr;
    const char * language_file = nullptr;
    const char * conjectures_file = nullptr;
    size_t conjecture_count = pomagma::DEFAULT_CONJECTURE_COUNT;

    if (argc == 4) {
        structure_file = argv[1];
        language_file = argv[2];
        conjectures_file = argv[3];
    } else if (argc == 5) {
        structure_file = argv[1];
        language_file = argv[2];
        conjectures_file = argv[3];
        conjecture_count = atoi(argv[4]);
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
    POMAGMA_ASSERT_EQ(
        structure.carrier().item_dim(),
        structure.carrier().item_count());

    // conjecture
    pomagma::conjecture(
        structure,
        language_file,
        conjectures_file,
        conjecture_count);

    return 0;
}
