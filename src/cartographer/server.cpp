#include "server.hpp"
#include "trim.hpp"
#include "aggregate.hpp"
#include "infer.hpp"
#include "messages.pb.h"
#include <zmq.hpp>

namespace pomagma
{

Server::Server (
        Structure & structure,
        const char * theory_file,
        const char * language_file)
    : m_structure(structure),
      m_theory_file(theory_file),
      m_language_file(language_file)
{
}

namespace detail
{

messaging::CartographerResponse call (
    messaging::CartographerRequest & request __attribute__((unused)))
{
    messaging::CartographerResponse response;
    TODO("dispatch on request type");
    return response;
}

} // namespace detail

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
        messaging::CartographerRequest request;
        request.ParseFromArray(raw_request.data(), raw_request.size());

        messaging::CartographerResponse response = detail::call(request);

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
