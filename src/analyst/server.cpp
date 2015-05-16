#include "server.hpp"
#include <pomagma/macrostructure/router.hpp>
#include <pomagma/language/language.hpp>
#include "messages.pb.h"
#include <zmq.hpp>
#include <algorithm>

namespace pomagma
{

Server::Server (
        const char * structure_file,
        const char * language_file,
        size_t thread_count)
    : m_language(load_language(language_file)),
      m_structure(structure_file),
      m_solution_set(m_structure.carrier()),
      m_approximator(m_structure),
      m_approximate_parser(m_approximator),
      m_probs(),
      m_routes(),
      m_simplifier(m_structure.signature(), m_routes, m_error_log),
      m_corpus(m_structure.signature()),
      m_validator(m_approximator, thread_count),
      m_parser(nullptr),
      m_virtual_machine()
{
    // parser and virtual_machine must be loaded after RETURN is delclared.
    Signature & signature = m_structure.signature();
    POMAGMA_ASSERT(
        not signature.unary_relation("RETURN"),
        "reserved name RETURN is defined in loaded structure");
    signature.declare("RETURN", m_solution_set);
    m_parser = new vm::Parser(signature);
    m_virtual_machine.load(signature);

    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    }

    Router router(m_structure.signature(), m_language);
    m_probs = router.measure_probs();
    m_routes = router.find_routes();
}

Server::~Server ()
{
    delete m_parser;
    for (const std::string & message : m_error_log) {
        POMAGMA_WARN(message);
    }
}

size_t Server::test_inference ()
{
    size_t fail_count = m_approximator.test();
    return fail_count;
}

std::string Server::simplify (const std::string & code)
{
    return m_simplifier.simplify(code);
}

Approximator::Validity Server::validate (const std::string & code)
{
    Approximation approx = m_approximate_parser.parse(code);
    return m_approximator.is_valid(approx);
}

std::vector<Validator::AsyncValidity> Server::validate_corpus (
        const std::vector<Corpus::LineOf<std::string>> & lines)
{
    auto linker = m_corpus.linker(lines, m_error_log);
    auto parsed = m_corpus.parse(lines, linker, m_error_log);
    return m_validator.validate(parsed, linker);
}

const Corpus::Histogram & Server::get_histogram ()
{
    return m_corpus.histogram();
}

std::unordered_map<std::string, float> Server::fit_language (
        const Corpus::Histogram & histogram)
{
    Router router(m_structure.signature(), m_language);
    router.fit_language(histogram.symbols, histogram.obs);
    m_language = router.get_language();

    POMAGMA_DEBUG("Language:")
    std::map<std::string, float> language(m_language.begin(), m_language.end());
    for (auto pair : language) {
        POMAGMA_DEBUG("\t" << pair.first << "\t" << pair.second);
    }

    m_probs = router.measure_probs();
    m_routes = router.find_routes();
    return m_language;
}

std::vector<std::string> Server::flush_errors ()
{
    std::vector<std::string> result;
    m_error_log.swap(result);
    return result;
}

std::vector<std::string> Server::solve (
    const std::string & program,
    size_t max_solutions)
{
    std::istringstream infile(program);
    auto listings = m_parser->parse(infile);
    POMAGMA_ASSERT_EQ(listings.size(), 1);
    vm::Listing listing = listings[0].first;

    m_solution_set.clear();
    m_virtual_machine.execute(listing);

    std::vector<Ob> obs;
    for (auto iter = m_solution_set.iter(); iter.ok(); iter.next()) {
        obs.push_back(*iter);
    }
    std::sort(obs.begin(), obs.end(), [this](const Ob & x, const Ob & y){
        return m_probs[x] > m_probs[y];
    });
    if (obs.size() > max_solutions) {
        obs.resize(max_solutions);
    }
    std::vector<std::string> solutions;
    for (auto ob : obs) {
        solutions.push_back(m_routes[ob]);
    }
    return solutions;
}

namespace
{

messaging::AnalystResponse handle (
    Server & server,
    messaging::AnalystRequest & request)
{
    POMAGMA_INFO("Handling request");
    messaging::AnalystResponse response;
    typedef messaging::AnalystResponse::Trool Trool;

    if (request.has_id()) {
        response.set_id(request.id());
    }

    if (request.has_test_inference()) {
        size_t fail_count = server.test_inference();
        response.mutable_test_inference()->set_fail_count(fail_count);
    }

    if (request.has_simplify()) {
        size_t code_count = request.simplify().codes_size();
        for (size_t i = 0; i < code_count; ++i) {
            const std::string & code = request.simplify().codes(i);
            std::string result = server.simplify(code);
            response.mutable_simplify()->add_codes(result);
        }
    }

    if (request.has_validate()) {
        size_t code_count = request.validate().codes_size();
        for (size_t i = 0; i < code_count; ++i) {
            const std::string & code = request.validate().codes(i);
            auto validity = server.validate(code);
            auto & result = * response.mutable_validate()->add_results();
            result.set_is_top(static_cast<Trool>(validity.is_top));
            result.set_is_bot(static_cast<Trool>(validity.is_bot));
            result.set_pending(false);
        }
    }

    if (request.has_validate_corpus()) {
        size_t line_count = request.validate_corpus().lines_size();
        std::vector<Corpus::LineOf<std::string>> lines(line_count);
        for (size_t i = 0; i < line_count; ++i) {
            const auto & line = request.validate_corpus().lines(i);
            if (line.has_name()) {
                lines[i].maybe_name = line.name();
            }
            lines[i].body = line.code();
        }
        const auto validities = server.validate_corpus(lines);
        auto & responses = * response.mutable_validate_corpus();
        for (const auto & pair : validities) {
            auto & result = * responses.add_results();
            result.set_is_top(static_cast<Trool>(pair.validity.is_top));
            result.set_is_bot(static_cast<Trool>(pair.validity.is_bot));
            result.set_pending(pair.pending);
        }
    }

    if (request.has_get_histogram()) {
        const Corpus::Histogram & histogram = server.get_histogram();
        auto & response_histogram =
            * response.mutable_get_histogram()->mutable_histogram();
        for (const auto & pair : histogram.obs) {
            auto & term = * response_histogram.add_terms();
            term.set_ob(pair.first);
            term.set_count(pair.second);
        }
        for (const auto & pair : histogram.symbols) {
            auto & term = * response_histogram.add_terms();
            term.set_name(pair.first);
            term.set_count(pair.second);
        }
    }

    if (request.has_fit_language()) {
        std::unordered_map<std::string, float> language;
        if (request.fit_language().has_histogram()) {
            Corpus::Histogram histogram;
            const auto & request_histogram =
                request.fit_language().histogram();
            size_t terms_size = request_histogram.terms_size();
            for (size_t i = 0; i < terms_size; ++i) {
                const auto & term = request_histogram.terms(i);
                if (term.has_ob()) {
                    histogram.obs[term.ob()] = term.count();
                } else {
                    histogram.symbols[term.name()] = term.count();
                }
            }
            language = server.fit_language(histogram);
        } else {
            language = server.fit_language(server.get_histogram());
        }
        auto & response_fit_language = * response.mutable_fit_language();
        for (const auto & pair : language) {
            auto & symbol = * response_fit_language.add_symbols();
            symbol.set_name(pair.first);
            symbol.set_prob(pair.second);
        }
    }

    if (request.has_solve()) {
        size_t max_solutions = std::numeric_limits<size_t>::max();
        if (request.solve().has_max_solutions()) {
            max_solutions = request.solve().max_solutions();
        }
        if (max_solutions > 0) {
            std::vector<std::string> solutions =
                server.solve(request.solve().program(), max_solutions);
            auto & response_solve = * response.mutable_solve();
            for (const auto & solution : solutions) {
                response_solve.add_solutions(solution);
            }
        } else {
            response.add_error_log(
                "expected request.solve.max_solutions > 0; actual 0");
        }
    }

    for (const std::string & message : server.flush_errors()) {
        response.add_error_log(message);
    }

    return response;
}

} // anonymous namespace

void Server::serve (const char * address)
{
    POMAGMA_INFO("Starting server");
    zmq::context_t context(1);
    zmq::socket_t socket(context, ZMQ_REP);
    socket.bind(address);

    while (true) {
        POMAGMA_DEBUG("waiting for request");
        zmq::message_t raw_request;
        socket.recv(& raw_request);

        POMAGMA_DEBUG("parsing request");
        messaging::AnalystRequest request;
        request.ParseFromArray(raw_request.data(), raw_request.size());

        messaging::AnalystResponse response = handle(* this, request);

        POMAGMA_DEBUG("serializing response");
        std::string response_str;
        response.SerializeToString(& response_str);
        const size_t size = response_str.length();
        zmq::message_t raw_response(size);
        memcpy(raw_response.data(), response_str.c_str(), size);

        POMAGMA_DEBUG("sending response");
        socket.send(raw_response);
    }
}

} // namespace pomagma
