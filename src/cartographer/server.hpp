#include <pomagma/macrostructure/structure.hpp>
#include <vector>
#include <map>

namespace pomagma
{

class Server
{
    Structure m_structure;
    const char * const m_theory_file;
    const char * const m_language_file;

public:

    Server (
        const char * structure_file,
        const char * theory_file,
        const char * language_file);

    void trim (
        bool temperature,
        size_t region_size,
        const std::vector<std::string> & regions_out);
    void aggregate (const std::string & survey_in);
    size_t assume (const std::string & facts_in);
    size_t infer (size_t priority);
    std::map<std::string, size_t> conjecture (
        const std::string & diverge_out,
        const std::string & equal_out,
        size_t max_count);
    void crop ();
    void validate ();
    void dump (const std::string & world_out);

    void serve (const char * address);
};

} // namespace pomagma
