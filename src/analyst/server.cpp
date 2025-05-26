#include <zmq.h>

#include <algorithm>
#include <iostream>
#include <limits>
#include <map>
#include <pomagma/analyst/propagate.hpp>
#include <pomagma/analyst/server.hpp>
#include <pomagma/atlas/macro/router.hpp>
#include <pomagma/language/language.hpp>
#include <sstream>
#include <unordered_map>

#include "analyst_messages.pb.h"

namespace pomagma {

Server::Server(const char* structure_file, const char* language_file)
    : m_language(load_language(language_file)),
      m_structure(structure_file),
      m_return(m_structure.carrier()),
      m_nreturn(m_structure.carrier()),
      m_dense_set_store(m_structure.carrier().item_dim()),
      m_worker_pool(),
      m_intervals_approximator(m_structure, m_dense_set_store, m_worker_pool),
      m_approximator(m_structure),
      m_approximate_parser(m_approximator),
      m_probs(),
      m_routes(),
      m_simplifier(m_structure.signature(), m_routes, m_error_log),
      m_corpus(m_structure.signature()),
      m_validator(m_approximator),
      m_parser(),
      m_virtual_machine() {
    // parser and virtual_machine must be loaded after RETURN is declared.
    Signature& signature = m_structure.signature();
    POMAGMA_ASSERT(not signature.unary_relation("RETURN"),
                   "reserved name RETURN is defined in loaded structure");
    POMAGMA_ASSERT(not signature.unary_relation("NRETURN"),
                   "reserved name NRETURN is defined in loaded structure");
    signature.declare("RETURN", m_return);
    signature.declare("NRETURN", m_nreturn);
    m_parser.load(signature);
    m_virtual_machine.load(signature);

    if (POMAGMA_DEBUG_LEVEL > 1) {
        m_structure.validate();
    }

    Router router(m_structure.signature(), m_language);
    m_probs = router.measure_probs();
    m_routes = router.find_routes();
}

Server::~Server() {
    for (const std::string& message : m_error_log) {
        POMAGMA_WARN(message);
    }
}

size_t Server::test_inference() {
    size_t fail_count = m_approximator.test();
    return fail_count;
}

std::string Server::simplify(const std::string& code) {
    return m_simplifier.simplify(code);
}

Approximator::Validity Server::validate(const std::string& code) {
    Approximation approx = m_approximate_parser.parse(code);
    return m_approximator.is_valid(approx);
}

std::vector<Validator::AsyncValidity> Server::validate_corpus(
    const std::vector<Corpus::LineOf<std::string>>& lines) {
    auto linker = m_corpus.linker(lines, m_error_log);
    auto parsed = m_corpus.parse(lines, linker, m_error_log);
    return m_validator.validate(parsed, linker);
}

const Corpus::Histogram& Server::get_histogram() {
    return m_corpus.histogram();
}

std::unordered_map<std::string, float> Server::fit_language(
    const Corpus::Histogram& histogram) {
    Router router(m_structure.signature(), m_language);
    router.fit_language(histogram.symbols, histogram.obs);
    m_language = router.get_language();

    POMAGMA_DEBUG("Language:")
    std::map<std::string, float> language(m_language.begin(), m_language.end());
    for (auto pair : language) {
        POMAGMA_DEBUG("\t" << pair.first << "\t" << pair.second);
    }

    m_probs = router.measure_probs();
    m_routes = router.find_routes();
    return m_language;
}

std::vector<std::string> Server::flush_errors() {
    std::vector<std::string> result;
    m_error_log.swap(result);
    return result;
}

void Server::print_ob_set(const DenseSet& set, std::vector<std::string>& result,
                          size_t max_count) const {
    std::vector<Ob> obs;
    for (auto iter = set.iter(); iter.ok(); iter.next()) {
        obs.push_back(*iter);
    }
    std::sort(obs.begin(), obs.end(), [this](const Ob& x, const Ob& y) {
        return m_probs[x] > m_probs[y];
    });
    if (obs.size() > max_count) {
        obs.resize(max_count);
    }
    for (auto ob : obs) {
        result.push_back(m_routes[ob]);
    }
}

Server::SolutionSet Server::solve(const std::string& program,
                                  size_t max_solutions) {
    std::istringstream infile(program);
    auto listings = m_parser.parse(infile);
    POMAGMA_ASSERT_LE(1, listings.size());

    m_return.clear();
    m_nreturn.clear();
    for (const auto& listing : listings) {
        vm::Program program = m_parser.find_program(listing);
        m_virtual_machine.execute(program);
    }
    POMAGMA_ASSERT(m_return.get_set().disjoint(m_nreturn.get_set()),
                   "inconsistent query result; check programs:\n"
                       << program);

    SolutionSet solutions;
    print_ob_set(m_return.get_set(), solutions.necessary, max_solutions);
    POMAGMA_ASSERT_LE(solutions.necessary.size(), max_solutions);
    max_solutions -= solutions.necessary.size();
    if (max_solutions > 0) {
        // TODO only execute NRETURN programs if needed
        DenseSet possible(m_structure.carrier().item_dim());
        possible.set_pnn(m_structure.carrier().support(), m_return.get_set(),
                         m_nreturn.get_set());
        print_ob_set(possible, solutions.possible, max_solutions);
    }
    return solutions;
}

pomagma::Trool Server::validate_facts(
    const std::vector<std::string>& polish_facts) {
    const auto theory = propagate::parse_theory(m_structure.signature(),
                                                polish_facts, m_error_log);
    return propagate::lazy_validate(theory, m_intervals_approximator);
}

static protobuf::AnalystResponse handle(Server& server,
                                        protobuf::AnalystRequest& request) {
    POMAGMA_INFO("Handling request");
    protobuf::AnalystResponse response;
    typedef protobuf::AnalystResponse::Trool Trool;

    if (!request.id().empty()) {
        response.set_id(request.id());
    }

    if (request.has_test_inference()) {
        size_t fail_count = server.test_inference();
        response.mutable_test_inference()->set_fail_count(fail_count);
    }

    if (request.has_simplify()) {
        size_t code_count = request.simplify().codes_size();
        for (size_t i = 0; i < code_count; ++i) {
            const std::string& code = request.simplify().codes(i);
            std::string result = server.simplify(code);
            response.mutable_simplify()->add_codes(result);
        }
    }

    if (request.has_validate()) {
        size_t code_count = request.validate().codes_size();
        for (size_t i = 0; i < code_count; ++i) {
            const std::string& code = request.validate().codes(i);
            auto validity = server.validate(code);
            auto& result = *response.mutable_validate()->add_results();
            result.set_is_top(static_cast<Trool>(validity.is_top));
            result.set_is_bot(static_cast<Trool>(validity.is_bot));
            result.set_pending(false);
        }
    }

    if (request.has_validate_corpus()) {
        size_t line_count = request.validate_corpus().lines_size();
        std::vector<Corpus::LineOf<std::string>> lines(line_count);
        for (size_t i = 0; i < line_count; ++i) {
            const auto& line = request.validate_corpus().lines(i);
            if (!line.name().empty()) {
                lines[i].maybe_name = line.name();
            }
            lines[i].body = line.code();
        }
        const auto validities = server.validate_corpus(lines);
        auto& responses = *response.mutable_validate_corpus();
        for (const auto& pair : validities) {
            auto& result = *responses.add_results();
            result.set_is_top(static_cast<Trool>(pair.validity.is_top));
            result.set_is_bot(static_cast<Trool>(pair.validity.is_bot));
            result.set_pending(pair.pending);
        }
    }

    if (request.has_get_histogram()) {
        const Corpus::Histogram& histogram = server.get_histogram();
        auto& response_histogram =
            *response.mutable_get_histogram()->mutable_histogram();
        for (const auto& pair : histogram.obs) {
            auto& term = *response_histogram.add_terms();
            term.set_ob(pair.first);
            term.set_count(pair.second);
        }
        for (const auto& pair : histogram.symbols) {
            auto& term = *response_histogram.add_terms();
            term.set_name(pair.first);
            term.set_count(pair.second);
        }
    }

    if (request.has_fit_language()) {
        std::unordered_map<std::string, float> language;
        if (request.fit_language().histogram().terms_size() > 0) {
            Corpus::Histogram histogram;
            const auto& request_histogram = request.fit_language().histogram();
            size_t terms_size = request_histogram.terms_size();
            for (size_t i = 0; i < terms_size; ++i) {
                const auto& term = request_histogram.terms(i);
                if (term.ob() != 0) {
                    histogram.obs[term.ob()] = term.count();
                } else {
                    histogram.symbols[term.name()] = term.count();
                }
            }
            language = server.fit_language(histogram);
        } else {
            language = server.fit_language(server.get_histogram());
        }
        auto& response_fit_language = *response.mutable_fit_language();
        for (const auto& pair : language) {
            auto& symbol = *response_fit_language.add_symbols();
            symbol.set_name(pair.first);
            symbol.set_prob(pair.second);
        }
    }

    if (request.has_solve()) {
        size_t max_solutions = std::numeric_limits<size_t>::max();
        if (request.solve().max_solutions() != 0) {
            max_solutions = request.solve().max_solutions();
        }
        if (max_solutions > 0) {
            Server::SolutionSet solutions =
                server.solve(request.solve().program(), max_solutions);
            auto& response_solve = *response.mutable_solve();
            for (const auto& solution : solutions.necessary) {
                response_solve.add_necessary(solution);
            }
            for (const auto& solution : solutions.possible) {
                response_solve.add_possible(solution);
            }
        } else {
            response.add_error_log(
                "expected request.solve.max_solutions > 0; actual 0");
        }
    }

    if (request.has_validate_facts()) {
        const auto& facts = request.validate_facts().facts();
        const std::vector<std::string> polish_facts(facts.begin(), facts.end());
        const auto result = server.validate_facts(polish_facts);
        response.mutable_validate_facts()->set_result(
            static_cast<Trool>(result));
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

    while (true) {
        POMAGMA_DEBUG("waiting for request");
        POMAGMA_ASSERT_C(0 == zmq_msg_init(&message));
        POMAGMA_ASSERT_C(-1 != zmq_msg_recv(&message, socket, 0));

        POMAGMA_DEBUG("parsing request");
        protobuf::AnalystRequest request;
        bool parsed = request.ParseFromArray(zmq_msg_data(&message),
                                             zmq_msg_size(&message));
        POMAGMA_ASSERT(parsed, "Failed to parse request");
        POMAGMA_ASSERT_C(0 == zmq_msg_close(&message));

        protobuf::AnalystResponse response = handle(*this, request);

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

}  // namespace pomagma
