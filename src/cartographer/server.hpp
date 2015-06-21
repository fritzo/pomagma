#include <pomagma/macrostructure/structure.hpp>
#include <vector>
#include <map>

namespace pomagma {

namespace protobuf {
class Signature;
} // namespace protobuf

class Server
{
    Structure m_structure;
    const char * const m_theory_file;
    const char * const m_language_file;
    bool m_serving;

public:

    Server (
        const char * structure_file,
        const char * theory_file,
        const char * language_file);

    struct TrimTask
    {
        bool temperature;
        size_t size;
        std::string filename;
    };
    void trim (const std::vector<TrimTask> & tasks);

    void aggregate (const std::string & survey_in);
    std::map<std::string, size_t> assume (const std::string & facts_in);
    size_t infer (size_t priority);
    std::map<std::string, size_t> conjecture (
        const std::string & diverge_out,
        const std::string & equal_out,
        size_t max_count);
    void crop ();
    void validate ();
    void dump (const std::string & world_out);

    struct Info
    {
        size_t item_count;
    };
    Info info ();

    void declare (protobuf::Signature & message);

    void stop ();

    void serve (const char * address);
};

} // namespace pomagma
