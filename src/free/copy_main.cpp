#include "util.hpp"
#include "structure.hpp"

int main (int argc, char ** argv)
{
    const char * structure_in = nullptr;
    const char * structure_out = nullptr;

    if (argc == 3) {
        structure_in = argv[1];
        structure_out = argv[2];
    } else {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << " structure_in structure_out" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    pomagma::Structure structure;
    structure.load(structure_in);
    structure.dump(structure_out);

    return 0;
}
