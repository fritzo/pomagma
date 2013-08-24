#include "server.hpp"
#include "simplify.hpp"
#include "approximate.hpp"
#include <pomagma/macrostructure/router.hpp>
#include <pomagma/language/language.hpp>
#include <zmq.hpp>

namespace pomagma
{

Server::Server (Structure & structure, const char * language_file)
{
    auto language = load_language(language_file);
    Router router(structure, language);
    m_probs = router.measure_probs();
    m_routes = router.find_routes();
}

void Server::serve (int port)
{
    zmq::context_t context(1);
    zmq::socket_t socket(context, ZMQ_REQ);
    std::ostringstream address;
    address << "tcp://*:" << port;
    socket.bind(address.str().c_str());

    while (true) {
        zmq::message_t request;
        socket.recv(& request);
        POMAGMA_DEBUG("receive request");

        zmq::message_t reply(4);
        memcpy((void *) reply.data(), "test", 4);
        socket.send(reply);
    }
}

} // namespace pomagma
