#include "util.hpp"
#include "scheduler.hpp"
#include "language.pb.h"
#include "structure.pb.h"
#include <zmq.hpp>
#include <unistd.h>

namespace pomagma
{

namespace messaging
{
    using namespace pomagma_messaging;
}

void ping (zmq::socket_t & socket)
{
    std::string message = "ping";
    zmq::message_t reply(4);
    socket.send(reply);
}

enum Command
{
    COMMAND_PING,
    COMMAND_CLEANUP,
    COMMAND_GROW,
    COMMAND_LOAD,
    COMMAND_DUMP,
    COMMAND_KILL
};

inline Command parse (const zmq::message_t &)
{
    // TODO parse message
    return COMMAND_PING;
}

void serve (const char * endpoint)
{
    zmq::context_t context(1);
    zmq::socket_t socket (context, ZMQ_REP);
    socket.bind(endpoint);

    while (true) {
        zmq::message_t request;
        socket.recv(&request);

        Command command = parse(request);

        switch (command) {
            case COMMAND_PING: { ping(socket); } break;
            case COMMAND_CLEANUP: { Scheduler::cleanup(); } break;
            case COMMAND_GROW: { Scheduler::grow(); } break;
            case COMMAND_LOAD: { Scheduler::load(); } break;
            case COMMAND_DUMP: { Scheduler::dump(); } break;
            case COMMAND_KILL: { abort(); } break;
        }
    }
}

} // namespace pomagma


int main (/* int argc, char ** argv */)
{
    // TODO add boost::program_options to set thread count etc.

    // TODO do not serve command parser; only use zmq to:
    // (1) load language
    // (2) load structure
    // (3) dump structure
    pomagma::serve("ipc:///tmp/pomagma");

    return 0;
}
