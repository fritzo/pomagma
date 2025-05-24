#include <pomagma/atlas/macro/carrier.hpp>

#include "conjecture_equal.hpp"

int main(int argc, char** argv) {
    pomagma::Log::Context log_context(argc, argv);

    const char* structure_file = nullptr;
    const char* language_file = nullptr;
    const char* conjectures_in_file = nullptr;
    const char* conjectures_out_file = nullptr;
    const char* theorems_file = nullptr;

    if (argc == 6) {
        structure_file = argv[1];
        language_file = argv[2];
        conjectures_in_file = argv[3];
        conjectures_out_file = argv[4];
        theorems_file = argv[5];
    } else {
        std::cout << "Usage: " << boost::filesystem::path(argv[0]).filename().string()
                  << " structure_in"
                  << " language_in"
                  << " conjectures_in"
                  << " conjectures_out"
                  << " theorems_out"
                  << "\n"
                  << "Environment Variables:\n"
                  << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE
                  << "\n"
                  << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL
                  << "\n";
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    // load structure
    pomagma::Structure structure;
    structure.load(structure_file);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        structure.validate();
    }
    POMAGMA_ASSERT_EQ(structure.carrier().item_dim(),
                      structure.carrier().item_count());

    // conjecture
    pomagma::try_prove_nless(structure, language_file, conjectures_in_file,
                             conjectures_out_file, theorems_file);

    return 0;
}
