#include "server.hpp"

int main(int argc, char** argv) {
    pomagma::Log::Context log_context(argc, argv);

    if (argc != 2) {
        std::cout << "Usage: " << boost::filesystem::basename(argv[0])
                  << " address"
                  << "\n"
                  << "Environment Variables:\n"
                  << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE
                  << "\n"
                  << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL
                  << "\n";
        POMAGMA_WARN("incorrect program args");
        exit(1);
    }

    const char* address = argv[1];

    pomagma::reducer::Server().serve(address);

    return 0;
}
