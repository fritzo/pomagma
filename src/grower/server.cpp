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

void load ()
{
    POMAGMA_ASSERT(not Scheduler::is_alive(),
            "tried to load while alive");
    TODO("load database");
}

void dump ()
{
    POMAGMA_ASSERT(not Scheduler::is_alive(),
            "tried to dump while alive");
    TODO("dump database");
}

enum Command
{
    COMMAND_PING,
    COMMAND_START,
    COMMAND_STOP,
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

    Scheduler::start();

    while (true) {
        zmq::message_t request;
        socket.recv(&request);

        Command command = parse(request);

        switch (command) {
            case COMMAND_START: { Scheduler::start(); } break;
            case COMMAND_STOP: { Scheduler::stop(); } break;
            case COMMAND_DUMP: { dump(); } break;
            case COMMAND_LOAD: { load(); } break;
            case COMMAND_PING: { ping(socket); } break;
            case COMMAND_KILL: { Scheduler::stop(); exit(0); } break;
        }
    }
}

} // namespace pomagma


int main (/* int argc, char ** argv */)
{
    // TODO add boost::program_options to set thread count etc.
    pomagma::serve("ipc:///tmp/pomagma");

    return 0;
}
