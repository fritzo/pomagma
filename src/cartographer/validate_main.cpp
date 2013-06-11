#include <pomagma/macrostructure/structure.hpp>

int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    const char * structure_in = nullptr;

    if (argc == 2) {
        structure_in = argv[1];
    } else {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << " structure" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    pomagma::Structure structure;
    structure.load(structure_in);
    structure.validate();

    return 0;
}
