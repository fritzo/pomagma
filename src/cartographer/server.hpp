#include <pomagma/macrostructure/structure.hpp>
#include <vector>

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

    void trim (
        size_t region_size,
        const std::vector<std::string> & regions_out);
    void aggregate (const std::string & survey_in);
    size_t infer ();
    void crop ();
    void validate ();
    void dump (const std::string & world_out);
};

} // namespace pomagma
