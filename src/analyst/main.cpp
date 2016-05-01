#include "server.hpp"

int main(int argc, char** argv) {
    pomagma::Log::Context log_context(argc, argv);

    if (argc != 4) {
        std::cout << "Usage: " << boost::filesystem::basename(argv[0])
                  << " structure language address"
                  << "\n"
                  << "Environment Variables:\n"
                  << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE
                  << "\n"
                  << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL
                  << "\n";
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    const char* structure_file = argv[1];
    const char* language_file = argv[2];
    const char* address = argv[3];

    pomagma::Server server(structure_file, language_file);
    server.serve(address);

    return 0;
}
