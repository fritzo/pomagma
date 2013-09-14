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

void Server::serve (const char * address)
{
    POMAGMA_INFO("Starting server");
    zmq::context_t context(1);
    zmq::socket_t socket(context, ZMQ_REP);
    socket.bind(address);

    while (true) {
        zmq::message_t request;
        POMAGMA_DEBUG("waiting for request");
        socket.recv(& request);
        POMAGMA_DEBUG("received request");

        // TODO dispatch on request type
        zmq::message_t response(4);
        memcpy((void *) response.data(), "test", 4);

        POMAGMA_DEBUG("sending response");
        socket.send(response);
        POMAGMA_DEBUG("sent response");
    }
}

} // namespace pomagma
