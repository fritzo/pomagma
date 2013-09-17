#include "server.hpp"
#include <pomagma/macrostructure/router.hpp>
#include <pomagma/language/language.hpp>
#include "messages.pb.h"
#include <zmq.hpp>

namespace pomagma
{

Server::Server (
        const char * structure_file,
        const char * language_file)
    : m_structure(structure_file),
      m_approximator(m_structure),
      m_probs(),
      m_routes(),
      m_simplifier(m_structure.signature(), m_routes)
{
    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    }

    auto language = load_language(language_file);
    Router router(m_structure.signature(), language);
    m_probs = router.measure_probs();
    m_routes = router.find_routes();
}

size_t Server::test ()
{
    size_t fail_count = m_approximator.validate();
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


namespace
{

messaging::AnalystResponse handle (
    Server & server,
    messaging::AnalystRequest & request)
{
    POMAGMA_INFO("Handling request");
    messaging::AnalystResponse response;

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
        TODO("validate corpus");
        response.mutable_validate();
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
