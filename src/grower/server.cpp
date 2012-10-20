#include "util.hpp"
#include "scheduler.hpp"
#include "language.pb.h"
#include "structure.pb.h"
#include <zmq.hpp>
#include <unistd.h>

namespace pomagma
{

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

inline std::string get_filename (const std::string & path)
{
    size_t pos = path.find_last_of("/");
    if (pos != std::string::npos) {
        return std::string(path.begin() + pos + 1, path.end());
    } else {
        return path;
    }
}

int main (int argc, char ** argv)
{
    if (argc != 4) {
        std::cout
            << "Usage: "
                << get_filename(argv[0])
                << " language_in structure_in structure_out" << "\n"
            << "Environment Variables:\n"
            << "  POMAGMA_SIZE = " << pomagma::DEFAULT_ITEM_DIM << "\n"
            << "  POMAGMA_THREADS = "
                << pomagma::DEFAULT_THREAD_COUNT << "\n"
            << "  POMAGMA_LOG_FILE = " << pomagma::DEFAULT_LOG_FILE << "\n"
            << "  POMAGMA_LOG_LEVEL = " << pomagma::DEFAULT_LOG_LEVEL << "\n"
            ;
        POMAGMA_WARN("expected 3 program args, got " << (argc - 1));
        exit(1);
    }

    const char * language_in = argv[1];
    const char * structure_in = argv[2];
    const char * structure_out = argv[3];
    const size_t thread_count = pomagma::getenv_default(
            "POMAGMA_THREADS",
            pomagma::DEFAULT_THREAD_COUNT);

    pomagma::load_langauge(language_in);
    pomagma::load_structure(structure_in);
    pomagma::Scheduler::set_thread_count(thread_count);
    pomagma::Scheduler::cleanup();
    pomagma::Scheduler::grow();
    pomagma::dump_structure(structure_out);

    return 0;
}
