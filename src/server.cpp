#include "util.hpp"
#include "scheduler.hpp"
#include <zmq.hpp>
#include <unistd.h>

namespace pomagma
{

void test (zmq::socket_t & socket)
{
    std::string message = "test";
    zmq::message_t reply(4);
    socket.send(reply);
}

void serve (const char * endpoint)
{
    zmq::context_t context(1);
    zmq::socket_t socket (context, ZMQ_REP);
    socket.bind(endpoint);

    Scheduler::start(4);

    while (true) {
        zmq::message_t request;
        socket.recv(&request);

        // TODO do something with message
        test(socket);
    }

    Scheduler::stopall();
}

} // namespace pomagma


int main ()
{
    pomagma::serve("ipc:///tmp/pomagma");

    return 0;
}
