#include "server.hpp"
#include "trim.hpp"
#include "aggregate.hpp"
#include "infer.hpp"
#include "signature.hpp"
#include <pomagma/theorist/assume.hpp>
#include <pomagma/theorist/conjecture_diverge.hpp>
#include <pomagma/theorist/conjecture_equal.hpp>
#include <pomagma/language/language.hpp>
#include <pomagma/atlas/world/structure_impl.hpp>
#include <pomagma/atlas/world/compact.hpp>
#include <pomagma/atlas/world/router.hpp>
#include <pomagma/atlas/world/vm.hpp>
#include "messages.pb.h"
#include <zmq.hpp>
#include <algorithm>

namespace pomagma {

Server::Server (
        const char * structure_file,
        const char * theory_file,
        const char * language_file)
    : m_structure(structure_file),
      m_theory_file(theory_file),
      m_language_file(language_file)
{
    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    }
}

void Server::trim (const std::vector<TrimTask> & tasks)
{
    compact(m_structure);
    const size_t item_count = m_structure.carrier().item_count();

    std::vector<TrimTask> sorted_tasks = tasks;
    std::sort(
        sorted_tasks.begin(),
        sorted_tasks.end(),
        [](const TrimTask & lhs, const TrimTask & rhs){
            return lhs.size > rhs.size;
        });
    const size_t task_count = sorted_tasks.size();
    #pragma omp parallel for schedule(dynamic, 1)
    for (size_t iter = 0; iter < task_count; ++iter) {
        const TrimTask & task = sorted_tasks[iter];
        if (task.size >= item_count) {

            if (task.size > item_count) {
                POMAGMA_WARN("trimming only " <<
                    item_count << " of " << task.size << " obs");
            }
            m_structure.dump(task.filename);

        } else {

            Structure region;
            region.init_carrier(task.size);
            extend(region.signature(), m_structure.signature());
            pomagma::trim(
                m_structure,
                region,
                m_theory_file,
                m_language_file,
                task.temperature);
            if (POMAGMA_DEBUG_LEVEL > 1) {
                region.validate();
            }
            region.dump(task.filename);
        }
    }
}

void Server::aggregate (const std::string & survey_in)
{
    Structure survey;
    survey.load(survey_in);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        survey.validate();
    }
    compact(m_structure);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    }
    DenseSet defined = restricted(survey.signature(), m_structure.signature());
    size_t total_dim =
        m_structure.carrier().item_count() + defined.count_items();
    if (m_structure.carrier().item_dim() < total_dim) {
        m_structure.resize(total_dim);
        if (POMAGMA_DEBUG_LEVEL > 1) {
            m_structure.validate();
        }
    }
    pomagma::aggregate(m_structure, survey, defined);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    }
}

std::map<std::string, size_t> Server::assume (const std::string & facts_in)
{
    auto counts = pomagma::assume(m_structure, facts_in.c_str());
    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    }
    return counts;
}

size_t Server::infer (size_t priority)
{
    size_t theorem_count = 0;
    switch (priority) {
        case 0: theorem_count = infer_pos(m_structure); break;
        case 1: theorem_count = infer_neg(m_structure); break;
        default: POMAGMA_WARN("unknown priority: " << priority); break;
    }
    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    }
    return theorem_count;
}

std::map<std::string, size_t> Server::conjecture (
    const std::string & diverge_out,
    const std::string & equal_out,
    size_t max_count)
{
    POMAGMA_ASSERT_LT(0, max_count);
    crop();

    std::vector<float> probs;
    std::vector<std::string> routes;
    auto language = load_language(m_language_file);
    {
        Router router(m_structure.signature(), language);
        probs = router.measure_probs();
        routes = router.find_routes();
    }

    std::map<std::string, size_t> counts;
    counts["diverge"] = pomagma::conjecture_diverge(
        m_structure,
        probs,
        routes,
        diverge_out.c_str());
    counts["equal"] = pomagma::conjecture_equal(
        m_structure,
        probs,
        routes,
        equal_out.c_str(),
        max_count);

    return counts;
}

void Server::crop (size_t headroom)
{
    compact(m_structure);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    }
    size_t item_count = m_structure.carrier().item_count() + headroom;
    if (item_count != m_structure.carrier().item_dim()) {
        m_structure.resize(item_count);
        if (POMAGMA_DEBUG_LEVEL > 1) {
            m_structure.validate();
        }
    }
}

void Server::validate ()
{
    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    } else {
        m_structure.validate_consistent();
    }
}

void Server::dump (const std::string & world_out)
{
    pomagma::compact(m_structure);
    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    }
    m_structure.log_stats();
    m_structure.dump(world_out);
}

Server::Info Server::info ()
{
    Info result;
    result.item_count = m_structure.carrier().item_count();
    return result;
}

void Server::declare (const std::string & name)
{
    Signature & signature = m_structure.signature();
    Carrier & carrier = m_structure.carrier();
    if (not signature.nullary_function(name)) {
        signature.declare(name, * new NullaryFunction(carrier));
    }
}

void Server::execute (const std::string & program)
{
    POMAGMA_DEBUG("parsing program");
    vm::ProgramParser parser(m_structure.signature());
    std::istringstream istream(program);
    const auto listings = parser.parse(istream);

    POMAGMA_DEBUG("executing " << listings.size() << " listings");
    vm::VirtualMachine virtual_machine;
    virtual_machine.load(m_structure.signature());
    for (const auto & listing : listings) {
        virtual_machine.execute(listing.first);
    }
}

void Server::stop ()
{
    m_serving = false;
}

namespace {

protobuf::CartographerResponse handle (
    Server & server,
    protobuf::CartographerRequest & request)
{
    POMAGMA_INFO("Handling request");
    Timer timer;
    protobuf::CartographerResponse response;

    if (request.has_crop()) {
        server.crop(request.crop().headroom());
        response.mutable_crop();
    }

    if (request.has_declare()) {
        for (const auto & name : request.declare().nullary_functions()) {
            server.declare(name);
        }
        response.mutable_declare();
    }

    if (request.has_assume()) {
        const std::string & facts_in = request.assume().facts_in();
        auto counts = server.assume(facts_in);
        response.mutable_assume()->set_pos_count(counts["pos"]);
        response.mutable_assume()->set_neg_count(counts["neg"]);
        response.mutable_assume()->set_merge_count(counts["merge"]);
        response.mutable_assume()->set_ignored_count(counts["ignored"]);
    }

    if (request.has_infer()) {
        const size_t priority = request.infer().priority();
        const size_t theorem_count = server.infer(priority);
        response.mutable_infer()->set_theorem_count(theorem_count);
    }

    if (request.has_execute()) {
        server.execute(request.execute().program());
        response.mutable_execute();
    }

    if (request.has_aggregate()) {
        server.aggregate(request.aggregate().survey_in());
        response.mutable_aggregate();
    }

    if (request.has_validate()) {
        server.validate();
        response.mutable_validate();
    }

    if (request.has_info()) {
        const auto info = server.info();
        response.mutable_info()->set_item_count(info.item_count);
    }

    if (request.has_dump()) {
        server.dump(request.dump().world_out());
        response.mutable_dump();
    }

    if (request.trim_size() > 0) {
        std::vector<Server::TrimTask> tasks(request.trim_size());
        for (int i = 0; i < request.trim_size(); ++i) {
            const auto & task = request.trim(i);
            tasks[i].size = task.size();
            tasks[i].temperature = task.temperature();
            tasks[i].filename = task.filename();
            response.add_trim();
        }
        server.trim(tasks);
    }

    if (request.has_conjecture()) {
        const std::string & diverge_out = request.conjecture().diverge_out();
        const std::string & equal_out = request.conjecture().equal_out();
        const size_t max_count = request.conjecture().max_count();
        auto counts = server.conjecture(diverge_out, equal_out, max_count);
        response.mutable_conjecture()->set_diverge_count(counts["diverge"]);
        response.mutable_conjecture()->set_equal_count(counts["equal"]);
    }

    if (request.has_stop()) {
        server.stop();
        response.mutable_stop();
    }

    POMAGMA_INFO("Handled request in " << timer.elapsed() << " sec");
    return response;
}

} // anonymous namespace

void Server::serve (const char * address)
{
    POMAGMA_INFO("Starting server");
    zmq::context_t context(1);
    zmq::socket_t socket(context, ZMQ_REP);
    socket.bind(address);

    for (m_serving = true; m_serving;) {
        POMAGMA_DEBUG("waiting for request");
        zmq::message_t raw_request;
        socket.recv(& raw_request);

        POMAGMA_DEBUG("parsing request");
        protobuf::CartographerRequest request;
        request.ParseFromArray(raw_request.data(), raw_request.size());

        protobuf::CartographerResponse response = handle(* this, request);

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
