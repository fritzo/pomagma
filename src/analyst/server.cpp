#include "server.hpp"
#include <pomagma/macrostructure/router.hpp>
#include <pomagma/language/language.hpp>
#include "messages.pb.h"
#include <zmq.hpp>

namespace pomagma
{

Server::Server (
        const char * structure_file,
        const char * language_file,
        size_t thread_count)
    : m_structure(structure_file),
      m_approximator(m_structure),
      m_approximate_parser(m_approximator),
      m_probs(),
      m_routes(),
      m_simplifier(m_structure.signature(), m_routes),
      m_corpus(m_structure.signature()),
      m_validator(m_approximator, thread_count)
{
    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    }

    auto language = load_language(language_file);
    Router router(m_structure.signature(), language);
    m_probs = router.measure_probs();
    m_routes = router.find_routes();
}

Server::~Server ()
{
    for (const std::string & message : m_error_log) {
        POMAGMA_WARN(message);
    }
}

size_t Server::test ()
{
    size_t fail_count = m_approximator.test();
    return fail_count;
}

std::string Server::simplify (const std::string & code)
{
    return m_simplifier.simplify(code);
}

size_t Server::batch_simplify (
        const std::string & codes_in,
        const std::string & codes_out)
{
    size_t line_count = pomagma::batch_simplify(
        m_structure,
        m_routes,
        codes_in.c_str(),
        codes_out.c_str());
    return line_count;
}

Approximator::Validity Server::is_valid (const std::string & code)
{
    Approximation approx = m_approximate_parser.parse(code);
    return m_approximator.is_valid(approx);
}

std::vector<Approximator::Validity> Server::validate_corpus (
        const std::vector<Corpus::LineOf<std::string>> & lines)
{
    auto parsed = m_corpus.parse(lines, m_error_log);
    return m_validator.validate(parsed);
}

std::vector<std::string> Server::flush_errors ()
{
    std::vector<std::string> result;
    m_error_log.swap(result);
    return result;
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

    if (request.has_test()) {
        size_t fail_count = server.test();
        response.mutable_test()->set_fail_count(fail_count);
    }

    if (request.has_simplify()) {
        size_t code_count = request.simplify().codes_size();
        for (size_t i = 0; i < code_count; ++i) {
            const std::string & code = request.simplify().codes(i);
            std::string result = server.simplify(code);
            response.mutable_simplify()->add_codes(result);
        }
    }

    if (request.has_batch_simplify()) {
        std::string codes_in = request.batch_simplify().codes_in();
        std::string codes_out = request.batch_simplify().codes_out();
        size_t line_count = server.batch_simplify(codes_in, codes_out);
        response.mutable_batch_simplify()->set_line_count(line_count);
    }

    if (request.has_validate()) {
        size_t code_count = request.validate().codes_size();
        for (size_t i = 0; i < code_count; ++i) {
            const std::string & code = request.validate().codes(i);
            auto validity = server.is_valid(code);
            auto & result = * response.mutable_validate()->add_results();
            result.set_is_top(static_cast<Trool>(validity.is_top));
            result.set_is_bot(static_cast<Trool>(validity.is_bot));
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
        for (const auto & validity : validities) {
            auto & result = * responses.add_results();
            result.set_is_top(static_cast<Trool>(validity.is_top));
            result.set_is_bot(static_cast<Trool>(validity.is_bot));
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
