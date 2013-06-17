#include <pomagma/macrostructure/structure.hpp>
#include <pomagma/macrostructure/router.hpp>
#include <pomagma/language/language.hpp>
#include "simplify.hpp"

int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    const char * structure_file = nullptr;
    const char * language_file = nullptr;
    const char * source_file = nullptr;
    const char * destin_file = nullptr;

    if (argc == 5) {
        structure_file = argv[1];
        language_file = argv[2];
        source_file = argv[3];
        destin_file = argv[4];
        POMAGMA_ASSERT_NE(std::string(source_file), std::string(destin_file));
    } else {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << " structure language source destin" << "\n"
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

    // compute routes
    std::vector<std::string> routes;
    {
        const auto language = pomagma::load_language(language_file);
        pomagma::Router router(structure, language);
        routes = router.find_routes();
    }

    // simplify
    pomagma::batch_simplify(
        structure,
        routes,
        source_file,
        destin_file);

    return 0;
}
