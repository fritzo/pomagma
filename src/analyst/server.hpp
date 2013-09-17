#include "simplify.hpp"
#include "approximate.hpp"
#include <pomagma/macrostructure/structure.hpp>

namespace pomagma
{

class Server
{
    Structure m_structure;
    Approximator m_approximator;
    std::vector<float> m_probs;
    std::vector<std::string> m_routes;
    SimplifyParser m_simplifier;

public:

    Server (
        const char * structure_file,
        const char * language_file);

    size_t test ();
    std::string simplify (const std::string & code);
    size_t batch_simplify (
            const std::string & codes_in,
            const std::string & codes_out);

    void serve (const char * address);
};

} // namespace pomagma
