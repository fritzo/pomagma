#include "server.hpp"
#include "trim.hpp"
#include "aggregate.hpp"
#include "infer.hpp"
#include "signature.hpp"
#include <pomagma/macrostructure/carrier.hpp>
#include <pomagma/macrostructure/structure.hpp>
#include <pomagma/macrostructure/compact.hpp>
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

namespace
{

messaging::CartographerResponse handle (
    messaging::CartographerRequest & request,
    Structure & structure,
    const char * theory_file,
    const char * language_file)
{
    POMAGMA_INFO("Handling request");
    const Carrier & carrier = structure.carrier();
    messaging::CartographerResponse response;

    if (request.has_trim()) {
        size_t region_count = request.trim().regions_out_size();
        size_t region_size = request.trim().size();
        if (carrier.item_dim() <= region_size) {
            compact(structure);
            #pragma omp parallel for schedule(dynamic, 1)
            for (size_t iter = 0; iter < region_count; ++iter) {
                structure.dump(request.trim().regions_out(iter));
            }
        } else {
            #pragma omp parallel for schedule(dynamic, 1)
            for (size_t iter = 0; iter < region_count; ++iter) {
                Structure region;
                region.init_carrier(region_size);
                extend(region.signature(), structure.signature());
                trim(structure, region, theory_file, language_file);
                region.dump(request.trim().regions_out(iter));
            }
        }
        response.mutable_trim();
    }

    if (request.has_aggregate()) {
        size_t survey_count = request.aggregate().surveys_in_size();
        for (size_t iter = 0; iter < survey_count; ++iter) {
            Structure survey;
            survey.load(request.aggregate().surveys_in(iter));
            DenseSet defined = restricted(
                survey.signature(),
                structure.signature());
            compact(structure);
            size_t total_dim = carrier.item_count() + defined.count_items();
            if (carrier.item_dim() < total_dim) {
                structure.resize(total_dim);
            }
            aggregate(structure, survey, defined);
        }
        response.mutable_aggregate();
    }

    if (request.has_infer()) {
        size_t theorem_count = infer_lazy(structure);
        response.mutable_infer()->set_theorem_count(theorem_count);
    }

    if (request.has_crop()) {
        pomagma::crop(structure);
        response.mutable_crop();
    }

    if (request.has_validate()) {
        if (POMAGMA_DEBUG_LEVEL > 1) {
            structure.validate();
        } else {
            structure.validate_consistent();
        }
        response.mutable_validate();
    }

    if (request.has_dump()) {
        const std::string & world_out = request.dump().world_out();
        pomagma::compact(structure);
        structure.dump(world_out.c_str());
        response.mutable_dump();
    }

    structure.log_stats();

    return response;
}

} // anonymous namespace

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

        messaging::CartographerResponse response = handle(
                request,
                m_structure,
                m_theory_file,
                m_language_file);

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
