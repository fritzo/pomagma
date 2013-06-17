#include <pomagma/macrostructure/structure.hpp>
#include <pomagma/macrostructure/router.hpp>
#include <pomagma/language/language.hpp>
#include "simplify.hpp"

namespace pomagma
{
namespace analyst
{

class Server
{
public:
    Server (Structure & structure, const char * language_file)
    {
        auto language = load_language(language_file);
        Router router(structure, language);
        m_probs = router.measure_probs();
        m_routes = router.find_routes();
    }

    void serve ()
    {
        POMAGMA_ERROR("TODO implement server");
    }

private:

    std::vector<float> m_probs;
    std::vector<std::string> m_routes;

};

} // namespace analyst
} // namespace pomagma


int main (int argc, char ** argv)
{
    pomagma::Log::Context log_context(argc, argv);

    const char * structure_file = nullptr;
    const char * language_file = nullptr;

    if (argc == 3) {
        structure_file = argv[1];
        language_file = argv[2];
    } else {
        std::cout
            << "Usage: "
                << pomagma::get_filename(argv[0])
                << " structure language" << "\n"
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

    // serve
    pomagma::analyst::Server server(structure, language_file);
    server.serve();

    return 0;
}
