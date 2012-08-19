#include "util.hpp"
#include "task_manager.hpp"
#include <zmq.hpp>
#include <unistd.h>

namespace pomagma
{

#define DEF_EXECUTE(POMAGMA_name)\
    void execute (const POMAGMA_name &)\
    { POMAGMA_INFO("executing " #POMAGMA_name) }

DEF_EXECUTE(EquationTask)
DEF_EXECUTE(NullaryFunctionTask)
DEF_EXECUTE(UnaryFunctionTask)
DEF_EXECUTE(BinaryFunctionTask)
DEF_EXECUTE(SymmetricFunctionTask)
DEF_EXECUTE(PositiveRelationTask)
DEF_EXECUTE(NegativeRelationTask)

#undef DEF_EXECUTE

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

    TaskManager::start(4);

    while (true) {
        zmq::message_t request;
        socket.recv(&request);

        // TODO do something with message
        test(socket);
    }

    TaskManager::stopall();
}

} // namespace pomagma


int main ()
{
    pomagma::serve("ipc:///tmp/pomagma");

    return 0;
}
