#include <pomagma/reducer/messages.pb.h>
#include <pomagma/reducer/server.hpp>
#include <zmq.h>

using pomagma::reducer::Ob;

namespace pomagma {
namespace reducer {

Server::Server() : engine_(), io_(engine_), error_log_(), serving_(false) {
    if (POMAGMA_DEBUG_LEVEL > 1) {
        engine_.validate(error_log_);
    }
}

Server::~Server() {
    for (const std::string& message : error_log_) {
        POMAGMA_WARN(message);
    }
}

bool Server::validate(std::vector<std::string>& errors) {
    return engine_.validate(errors);
}

std::string Server::reduce(const std::string& code, size_t budget) {
    std::string result;
    if (Ob ob = io_.parse(code, error_log_)) {
        Ob red = engine_.reduce(ob, budget);
        result = io_.print(red);
    }
    return result;
}

std::vector<std::string> Server::flush_errors() {
    std::vector<std::string> result;
    error_log_.swap(result);
    return result;
}

static protobuf::ReducerResponse handle(Server& server,
                                        protobuf::ReducerRequest& request) {
    POMAGMA_INFO("Handling request");
    protobuf::ReducerResponse response;

    if (request.has_id()) {
        response.set_id(request.id());
    }

    if (request.has_reduce()) {
        size_t budget = request.reduce().budget();
        std::string code = request.reduce().code();
        code = server.reduce(code, budget);
        response.mutable_reduce()->set_code(code);
        response.mutable_reduce()->set_budget(budget);
    }

    if (request.has_validate()) {
        std::vector<std::string> errors;
        const bool valid = server.validate(errors);
        response.mutable_validate()->set_valid(valid);
        for (const std::string& error : errors) {
            response.mutable_validate()->add_errors(error);
        }
    }

    for (const std::string& message : server.flush_errors()) {
        response.add_error_log(message);
    }

    return response;
}

#define POMAGMA_ASSERT_C(cond) \
    POMAGMA_ASSERT((cond), "Failed (" #cond "): " << strerror(errno))

void Server::serve(const char* address) {
    void* context;
    void* socket;
    zmq_msg_t message;

    POMAGMA_INFO("Starting server");
    POMAGMA_ASSERT_C((context = zmq_ctx_new()));
    POMAGMA_ASSERT_C((socket = zmq_socket(context, ZMQ_REP)));
    POMAGMA_ASSERT_C(0 == zmq_bind(socket, address));

    for (serving_ = true; serving_;) {
        POMAGMA_DEBUG("waiting for request");
        POMAGMA_ASSERT_C(0 == zmq_msg_init(&message));
        POMAGMA_ASSERT_C(-1 != zmq_msg_recv(&message, socket, 0));

        POMAGMA_DEBUG("parsing request");
        protobuf::ReducerRequest request;
        bool parsed = request.ParseFromArray(zmq_msg_data(&message),
                                             zmq_msg_size(&message));
        POMAGMA_ASSERT(parsed, "Failed to parse request");
        POMAGMA_ASSERT_C(0 == zmq_msg_close(&message));

        protobuf::ReducerResponse response = handle(*this, request);

        POMAGMA_DEBUG("serializing response");
        std::string response_str;
        response.SerializeToString(&response_str);
        const int size = response_str.length();
        POMAGMA_ASSERT_C(0 == zmq_msg_init(&message));
        POMAGMA_ASSERT_C(0 == zmq_msg_init_size(&message, size));
        memcpy(zmq_msg_data(&message), response_str.c_str(), size);

        POMAGMA_DEBUG("sending response");
        POMAGMA_ASSERT_C(size == zmq_msg_send(&message, socket, 0));
        POMAGMA_ASSERT_C(0 == zmq_msg_close(&message));
    }
}

}  // namespace reducer
}  // namespace pomagma
