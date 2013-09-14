#include <pomagma/macrostructure/structure.hpp>

namespace pomagma
{

class Server
{
    Structure & m_structure;
    const char * const m_theory_file;
    const char * const m_language_file;

public:

    Server (
        Structure & structure,
        const char * theory_file,
        const char * language_file);

    void serve (const char * address);
};

} // namespace pomagma
