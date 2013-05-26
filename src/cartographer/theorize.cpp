#include "theorize.hpp"
#include "carrier.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "binary_relation.hpp"
#include "symmetric_function.hpp"
#include <pomagma/language/language.pb.h>
#include <deque>

namespace pomagma
{

std::unordered_map<std::string, float> load_language (
        const char * language_file)
{
    POMAGMA_INFO("Loading languge");

    messaging::Language language;

    std::ifstream file(language_file, std::ios::in | std::ios::binary);
    POMAGMA_ASSERT(file.is_open(),
        "failed to open language file " << language_file);
    POMAGMA_ASSERT(language.ParseFromIstream(&file),
        "failed tp parse language file " << language_file);

    std::unordered_map<std::string, float> result;
    for (int i = 0; i < language.terms_size(); ++i) {
        const auto & term = language.terms(i);
        POMAGMA_DEBUG("setting P(" << term.name() << ") = " << term.weight());
        result[term.name()] = term.weight();
    }

    return result;
}

std::vector<float> measure_weights (
        Structure & structure,
        const std::unordered_map<std::string, float> & language)
{
    POMAGMA_INFO("Measuring ob weights");
    POMAGMA_ASSERT(not language.empty(), "language is empty");

    const size_t item_count = structure.carrier().item_count();
    std::vector<float> weights(1 + item_count, 0);

    POMAGMA_ERROR("TODO");

    return weights;
}

struct LocalParse
{
    enum Arity { NONE, NULLARY, INJECTIVE, BINARY };
    Arity arity;
    std::string name;
    Ob arg1;
    Ob arg2;

    LocalParse () : arity(NONE), name(), arg1(0), arg2(0) {}
    LocalParse (Arity a, const std::string & n, Ob a1=0, Ob a2=0)
        : arity(a),
          name(n),
          arg1(a1),
          arg2(a2)
    {
    }
};

std::vector<std::string> parse_all (
        Structure & structure,
        const std::unordered_map<std::string, float> & language)
{
    POMAGMA_INFO("Parsing all obs");
    POMAGMA_ASSERT(not language.empty(), "language is empty");

    const size_t item_count = structure.carrier().item_count();
    std::vector<LocalParse> max_parses(1 + item_count);
    std::vector<float> max_weights(1 + item_count, 0);

    // initialize nullary functions
    for (auto pair : structure.signature().nullary_functions()) {
        const auto & name = pair.first;
        const auto & fun = * pair.second;
        Ob ob = fun.find();
        max_parses[ob] = LocalParse(LocalParse::NULLARY, name);
        max_weights[ob] = language.find(name)->second;
    }

    // iteratively find best local parses
    // TODO parallelize
    bool changed = true;
    while (changed) {
        changed = false;
        for (auto iter = structure.carrier().iter(); iter.ok(); iter.next()) {
            POMAGMA_ERROR("TODO find best parse of ob");
        }
    }

    // find full parses
    std::vector<std::string> parses(1 + item_count);
    std::deque<Ob> parse_queue;
    for (auto iter = structure.carrier().iter(); iter.ok(); iter.next()) {
        Ob ob = * iter;
        parse_queue.push_back(ob);
    }
    while (not parse_queue.empty()) {
        Ob ob = parse_queue.front();
        parse_queue.pop_front();

        auto parse = max_parses[ob];
        switch (parse.arity) {
            case LocalParse::NONE: {
                POMAGMA_ERROR("ob has no local parse: " << ob);
            } break;

            case LocalParse::NULLARY: {
                parses[ob] = parse.name;
            } break;

            case LocalParse::INJECTIVE: {
                const auto & arg = parses[parse.arg1];
                if (arg.empty()) {
                    parse_queue.push_back(ob);
                } else {
                    parses[ob] = parse.name + " " + arg;
                }
            } break;

            case LocalParse::BINARY: {
                const auto & lhs = parses[parse.arg1];
                const auto & rhs = parses[parse.arg2];
                if (lhs.empty() or rhs.empty()) {
                    parse_queue.push_back(ob);
                } else {
                    parses[ob] = parse.name + " " + lhs + " " + rhs;
                }
            } break;
        }
    }

    return parses;
}

void theorize (
        Structure & structure,
        const std::vector<float> & weights,
        const std::vector<std::string> & parses,
        const char * conjectures_file,
        size_t max_count)
{
    POMAGMA_INFO("Conjecturing equations");
    auto & signature = structure.signature();

    const BinaryRelation & nless = * signature.binary_relations("NLESS");

    POMAGMA_DEBUG("collecting conjectures");
    std::vector<std::pair<Ob, Ob>> conjectures;
    for (auto iter = structure.carrier().iter(); iter.ok(); iter.next()) {
        Ob lhs = * iter;
        for (auto iter = structure.carrier().iter(); iter.ok(); iter.next()) {
            Ob rhs = * iter;
            if (rhs >= lhs) { break; }
            if (nless.find_Lx(lhs, rhs)) { continue; }
            if (nless.find_Rx(rhs, lhs)) { continue; }
            conjectures.push_back(std::make_pair(lhs, rhs));
        }
    }

    POMAGMA_DEBUG("sorting conjectures");
    max_count = std::min(max_count, conjectures.size());
    auto sort_by_weight = [&](
            const std::pair<Ob, Ob> & x,
            const std::pair<Ob, Ob> & y)
    {
        return weights[x.first] * weights[x.second]
             > weights[y.first] * weights[y.second];
    };

    std::nth_element(
            conjectures.begin(),
            conjectures.begin() + max_count,
            conjectures.end(),
            sort_by_weight);
    conjectures.resize(max_count);
    std::sort(conjectures.begin(), conjectures.end(), sort_by_weight);

    POMAGMA_DEBUG("writing conjectures to " << conjectures_file);
    std::ofstream file(conjectures_file, std::ios::out);
    POMAGMA_ASSERT(file, "failed to open " << conjectures_file);
    file << "# conjectures generated by pomagma";
    for (auto pair : conjectures) {
        const auto & lhs = parses[pair.first];
        const auto & rhs = parses[pair.second];
        file << "\nEQUAL " << lhs << " " << rhs;
    }
}

} // namespace pomagma
