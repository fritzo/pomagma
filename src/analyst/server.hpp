#include "simplify.hpp"
#include "approximate.hpp"
#include "corpus.hpp"
#include "validator.hpp"
#include <pomagma/macrostructure/structure.hpp>

namespace pomagma
{

class Server
{
    Structure m_structure;
    Approximator m_approximator;
    ApproximateParser m_approximate_parser;
    std::vector<float> m_probs;
    std::vector<std::string> m_routes;
    SimplifyParser m_simplifier;
    Corpus m_corpus;
    Validator m_validator;
    std::vector<std::string> m_error_log;

public:

    Server (
        const char * structure_file,
        const char * language_file,
        size_t thread_count);
    ~Server ();

    size_t test ();
    std::string simplify (const std::string & code);
    size_t batch_simplify (
            const std::string & codes_in,
            const std::string & codes_out);
    Approximator::Validity is_valid (const std::string & code);
    std::vector<Approximator::Validity> validate_corpus (
            const std::vector<Corpus::Line> & lines);

    std::vector<std::string> flush_errors ();

    void serve (const char * address);
};

} // namespace pomagma
