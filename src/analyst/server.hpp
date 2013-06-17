#include <pomagma/macrostructure/structure.hpp>

namespace pomagma
{

class Server
{
public:

    Server (Structure & structure, const char * language_file);

    void serve ();

private:

    std::vector<float> m_probs;
    std::vector<std::string> m_routes;
};

} // namespace pomagma
