#include "server.hpp"
#include <pomagma/macrostructure/router.hpp>
#include <pomagma/language/language.hpp>

namespace pomagma
{

Server::Server (Structure & structure, const char * language_file)
{
    auto language = load_language(language_file);
    Router router(structure, language);
    m_probs = router.measure_probs();
    m_routes = router.find_routes();
}

void Server::serve ()
{
    POMAGMA_ERROR("TODO implement server");
}

} // namespace pomagma
