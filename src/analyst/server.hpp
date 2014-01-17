#include "simplify.hpp"
#include "approximate.hpp"
#include "corpus.hpp"
#include "validator.hpp"
#include <pomagma/macrostructure/structure.hpp>

namespace pomagma
{

class Server
{
    std::unordered_map<std::string, float> m_language;
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

    size_t test_inference ();
    std::string simplify (const std::string & code);
    Approximator::Validity validate (const std::string & code);
    std::vector<Validator::AsyncValidity> validate_corpus (
            const std::vector<Corpus::LineOf<std::string>> & lines);
    const Corpus::Histogram & get_histogram ();
    std::unordered_map<std::string, float> fit_language (
            const Corpus::Histogram & histogram);

    std::vector<std::string> flush_errors ();

    void serve (const char * address);
};

} // namespace pomagma
