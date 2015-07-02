#include "simplify.hpp"
#include "approximate.hpp"
#include "corpus.hpp"
#include "validator.hpp"
#include <pomagma/atlas/world/structure.hpp>
#include <pomagma/atlas/world/vm.hpp>

namespace pomagma
{

class Server
{
    std::unordered_map<std::string, float> m_language;
    Structure m_structure;
    UnaryRelation m_return;
    UnaryRelation m_nreturn;
    Approximator m_approximator;
    ApproximateParser m_approximate_parser;
    std::vector<float> m_probs;
    std::vector<std::string> m_routes;
    Simplifier m_simplifier;
    Corpus m_corpus;
    Validator m_validator;
    vm::ProgramParser * m_parser;
    vm::VirtualMachine m_virtual_machine;
    std::vector<std::string> m_error_log;

public:

    Server (
        const char * structure_file,
        const char * language_file,
        size_t thread_count);
    ~Server ();

    struct SolutionSet
    {
        std::vector<std::string> necessary;
        std::vector<std::string> possible;
    };

    size_t test_inference ();
    std::string simplify (const std::string & code);
    Approximator::Validity validate (const std::string & code);
    std::vector<Validator::AsyncValidity> validate_corpus (
            const std::vector<Corpus::LineOf<std::string>> & lines);
    const Corpus::Histogram & get_histogram ();
    std::unordered_map<std::string, float> fit_language (
            const Corpus::Histogram & histogram);
    SolutionSet solve (const std::string & program, size_t max_solutions);

    void serve (const char * address);

    std::vector<std::string> flush_errors ();

private:

    void print_ob_set (
            const DenseSet & set,
            std::vector<std::string> & result,
            size_t max_count) const;
};

} // namespace pomagma
