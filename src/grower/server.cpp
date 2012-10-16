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

void load_langauge (const char * endpoint)
{
    zmq::context_t context(1);
    zmq::socket_t socket (context, ZMQ_REP);
    socket.bind(endpoint);

    zmq::message_t request;
    socket.recv(&request);

    messaging::Language language;
    language.ParseFromArray(request.data(), request.size());

    TODO("load language");
}

void load_structure (const char * endpoint)
{
    zmq::context_t context(1);
    zmq::socket_t socket (context, ZMQ_REP);
    socket.bind(endpoint);

    TODO("load structure");
}

void dump_structure (const char * endpoint)
{
    zmq::context_t context(1);
    zmq::socket_t socket (context, ZMQ_REP);
    socket.bind(endpoint);

    TODO("dump structure");

    std::string message = "ping";
    zmq::message_t reply(4);
    socket.send(reply);}

} // namespace pomagma

using namespace pomagma;

int main (int argc, char ** argv)
{
    if (argc != 4) {
        std::cout
            << "Usage: "
            << argv[0]
            << " language_in"
            << " structure_in"
            << " structure_out"
            << std::endl;
        POMAGMA_WARN("expected 3 program args, got " << (argc - 1));
        exit(1);
    }

    const char * language_in = argv[1];
    const char * structure_in = argv[2];
    const char * structure_out = argv[3];

    pomagma::load_langauge(language_in);
    pomagma::load_structure(structure_in);
    pomagma::Scheduler::cleanup();
    pomagma::Scheduler::grow();
    pomagma::dump_structure(structure_out);

    return 0;
}
