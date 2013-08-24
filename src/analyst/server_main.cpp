#include "server.hpp"

int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    if (argc != 4) {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << " structure language port" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    const char * structure_file = argv[1];
    const char * language_file = argv[2];
    const int port = atoi(argv[3]);

    // load structure
    pomagma::Structure structure;
    structure.load(structure_file);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        structure.validate();
    }

    // serve
    pomagma::Server server(structure, language_file);
    server.serve(port);

    return 0;
}
