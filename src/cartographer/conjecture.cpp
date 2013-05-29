#include "conjecture.hpp"
#include "carrier.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "binary_relation.hpp"
#include "symmetric_function.hpp"
#include "compact.hpp"
#include "scheduler.hpp"
#include <pomagma/util/language.hpp>
#include <deque>
#include <cstdlib>
#include <unistd.h> // for fork
#include <sys/wait.h> // for wait

namespace pomagma
{

namespace detail
{

class Router
{
public:

    Router (
        Structure & structure,
        const std::unordered_map<std::string, float> & language);

    std::vector<float> measure_probs (float reltol = 0.1) const;
    std::vector<std::string> find_routes () const;

private:

    enum Arity { NULLARY, INJECTIVE, BINARY };

    struct SegmentType
    {
        Arity arity;
        std::string name;
        float prob;

        SegmentType () {}
        SegmentType (Arity a, const std::string & n, float p)
            : arity(a),
              name(n),
              prob(p)
        {}
    };

    typedef uint32_t TypeId;

    struct Segment
    {
        TypeId type;
        Ob val;
        Ob arg1;
        Ob arg2;

        Segment () {}
        Segment (TypeId t, Ob v, Ob a1=0, Ob a2=0)
            : type(t),
              val(v),
              arg1(a1),
              arg2(a2)
        {}
    };

    TypeId new_type (Arity arity, const std::string & name)
    {
        auto i = m_language.find(name);
        float prob = i == m_language.end() ? 0.f : i->second;
        m_types.push_back(SegmentType(arity, name, prob));
        return m_types.size() - 1;
    }

    typedef std::vector<Segment>::const_iterator Iterator;

    Range<Iterator> iter_val (Ob val) const
    {
        size_t begin = m_value_index[val - 1];
        size_t end = m_value_index[val] + 1;
        return range(m_segments.begin() + begin, m_segments.begin() + end);
    }

    Carrier & m_carrier;
    const std::unordered_map<std::string, float> m_language;
    std::vector<SegmentType> m_types;
    std::vector<Segment> m_segments;
    std::vector<size_t> m_value_index;
};

Router::Router (
        Structure & structure,
        const std::unordered_map<std::string, float> & language)
    : m_carrier(structure.carrier()),
      m_language(language),
      m_value_index(structure.carrier().item_count())
{
    POMAGMA_ASSERT(not language.empty(), "language is empty");
    Signature & signature = structure.signature();

    POMAGMA_INFO("Building router indices");

    for (auto pair : signature.nullary_functions()) {
        const auto & name = pair.first;
        const auto & fun = * pair.second;
        const TypeId type = new_type(NULLARY, name);
        if (Ob val = fun.find()) {
            m_segments.push_back(Segment(type, val));
        }
    }

    for (auto pair : signature.injective_functions()) {
        const auto & name = pair.first;
        const auto & fun = * pair.second;
        const TypeId type = new_type(INJECTIVE, name);
        for (auto iter = fun.iter(); iter.ok(); iter.next()) {
            Ob arg = * iter;
            Ob val = fun.find(arg);
            m_segments.push_back(Segment(type, val, arg));
        }
    }

    for (auto pair : signature.binary_functions()) {
        const auto & name = pair.first;
        const auto & fun = * pair.second;
        const TypeId type = new_type(BINARY, name);
        for (auto iter = m_carrier.iter(); iter.ok(); iter.next()) {
            Ob lhs = * iter;
            for (auto iter = fun.iter_lhs(lhs); iter.ok(); iter.next()) {
                Ob rhs = * iter;
                Ob val = fun.find(lhs, rhs);
                m_segments.push_back(Segment(type, val, lhs, rhs));
            }
        }
    }

    for (auto pair : signature.symmetric_functions()) {
        const auto & name = pair.first;
        const auto & fun = * pair.second;
        const TypeId type = new_type(BINARY, name);
        for (auto iter = m_carrier.iter(); iter.ok(); iter.next()) {
            Ob lhs = * iter;
            for (auto iter = fun.iter_lhs(lhs); iter.ok(); iter.next()) {
                Ob rhs = * iter;
                Ob val = fun.find(lhs, rhs);
                m_segments.push_back(Segment(type, val, lhs, rhs));
            }
        }
    }

    std::sort(
        m_segments.begin(),
        m_segments.end(),
        [&](const Segment & x, const Segment & y){
            return std::tie(x.val, x.type, x.arg1, x.arg2)
                 < std::tie(y.val, y.type, y.arg1, y.arg2);
        });

    // assume all values are reached by at least one segment
    m_value_index.resize(1 + m_carrier.item_count(), 0);
    for (size_t i = 0; i < m_segments.size(); ++i) {
        m_value_index[m_segments[i].val] = i;
    }
}

std::vector<float> Router::measure_probs (float reltol) const
{
    POMAGMA_INFO("Measuring ob probs");
    const size_t item_count = m_carrier.item_count();
    std::vector<float> probs(1 + item_count, 0);

    const float max_increase = 1.0 + reltol;
    bool changed = true;
    while (changed) {
        changed = false;

        POMAGMA_INFO("accumulating route probabilities");

        # pragma omp parallel for schedule(dynamic, 1)
        for (size_t i = 0; i < item_count; ++i) {
            Ob ob = 1 + i;

            float prob = 0;
            for (const Segment & segment : iter_val(ob)) {
                const SegmentType & type = m_types[segment.type];
                switch (type.arity) {
                    case NULLARY: {
                        prob += type.prob;
                    } break;

                    case INJECTIVE: {
                        Ob arg = segment.arg1;
                        prob += type.prob * probs[arg];
                    } break;

                    case BINARY: {
                        Ob lhs = segment.arg1;
                        Ob rhs = segment.arg2;
                        prob += type.prob * probs[lhs] * probs[rhs];
                    } break;
                }
            }

            if (prob > probs[ob] * max_increase) {
                #pragma omp atomic
                changed |= true;
            }
            probs[ob] = prob; // relaxed memory order
        }
    }

    return probs;
}

std::vector<std::string> Router::find_routes () const
{
    POMAGMA_INFO("Routing all obs");

    const size_t item_count = m_carrier.item_count();
    std::vector<float> best_probs(1 + item_count, 0);
    std::vector<Segment> best_segments(1 + item_count);

    bool changed = true;
    while (changed) {
        changed = false;

        POMAGMA_INFO("finding best local routes");

        #pragma omp parallel for schedule(dynamic, 1)
        for (size_t i = 0; i < item_count; ++i) {
            Ob ob = 1 + i;

            float & best_prob = best_probs[ob];
            Segment & best_segment = best_segments[ob];
            bool best_changed = false;
            for (const Segment & segment : iter_val(ob)) {
                const SegmentType & type = m_types[segment.type];
                float prob = 0;
                switch (type.arity) {
                    case NULLARY: {
                        prob = type.prob;
                    } break;

                    case INJECTIVE: {
                        Ob arg = segment.arg1;
                        prob = type.prob * best_probs[arg];
                    } break;

                    case BINARY: {
                        Ob lhs = segment.arg1;
                        Ob rhs = segment.arg2;
                        prob = type.prob * best_probs[lhs] * best_probs[rhs];
                    } break;
                }
                if (unlikely(prob > best_prob)) {
                    best_prob = prob; // relaxed memory order
                    best_segment = segment; // relaxed memory order
                    best_changed = true;
                }
            }

            if (best_changed) {
                #pragma omp atomic
                changed |= true;
            }
        }
    }

    POMAGMA_DEBUG("scheduling route building");
    std::vector<Ob> schedule;
    schedule.reserve(item_count);
    for (auto iter = m_carrier.iter(); iter.ok(); iter.next()) {
        Ob ob = * iter;
        POMAGMA_ASSERT_LT(0, best_probs[ob]);
        schedule.push_back(ob);
    }
    std::sort(
        schedule.begin(),
        schedule.end(),
        [&](const Ob & x, const Ob & y){
            return best_probs[x] > best_probs[y];
        });

    POMAGMA_DEBUG("building full routes");
    std::vector<std::string> routes(1 + item_count);
    for (Ob ob : schedule) {

        const Segment & segment = best_segments[ob];
        const SegmentType & type = m_types[segment.type];
        switch (type.arity) {
            case NULLARY: {
                routes[ob] = type.name;
            } break;

            case INJECTIVE: {
                const auto & arg = routes[segment.arg1];
                POMAGMA_ASSERT(not arg.empty(), "unknown arg route");
                routes[ob] = type.name + " " + arg;
            } break;

            case BINARY: {
                const auto & lhs = routes[segment.arg1];
                const auto & rhs = routes[segment.arg2];
                POMAGMA_ASSERT(not lhs.empty(), "unknown lhs route");
                POMAGMA_ASSERT(not rhs.empty(), "unknown rhs route");
                routes[ob] = type.name + " " + lhs + " " + rhs;
            } break;
        }
    }

    return routes;
}

std::vector<std::pair<Ob, Ob>> conjecture (
        Structure & structure,
        const std::vector<float> & probs,
        const std::vector<std::string> & routes,
        const char * conjectures_file,
        size_t max_count)
{
    POMAGMA_INFO("Conjecturing " << max_count << " equations");
    auto & signature = structure.signature();
    const Carrier & carrier = structure.carrier();
    const BinaryRelation & nless = * signature.binary_relations("NLESS");

    POMAGMA_DEBUG("collecting conjectures");
    std::vector<std::pair<Ob, Ob>> conjectures;
    for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
        Ob lhs = * iter;
        for (auto iter = carrier.iter(); iter.ok(); iter.next()) {
            Ob rhs = * iter;
            if (rhs >= lhs) { break; }
            if (nless.find_Lx(lhs, rhs)) { continue; }
            if (nless.find_Rx(rhs, lhs)) { continue; }
            conjectures.push_back(std::make_pair(lhs, rhs));
        }
    }

    POMAGMA_DEBUG("sorting conjectures");
    max_count = std::min(max_count, conjectures.size());
    auto sort_by_prob = [&](
            const std::pair<Ob, Ob> & x,
            const std::pair<Ob, Ob> & y)
    {
        return probs[x.first] * probs[x.second]
             > probs[y.first] * probs[y.second];
    };

    std::nth_element(
            conjectures.begin(),
            conjectures.begin() + max_count,
            conjectures.end(),
            sort_by_prob);
    conjectures.resize(max_count);
    std::sort(conjectures.begin(), conjectures.end(), sort_by_prob);

    POMAGMA_DEBUG("writing conjectures to " << conjectures_file);
    std::ofstream file(conjectures_file, std::ios::out);
    POMAGMA_ASSERT(file, "failed to open " << conjectures_file);
    file << "# conjectures generated by pomagma";
    for (auto pair : conjectures) {
        const auto & lhs = routes[pair.first];
        const auto & rhs = routes[pair.second];
        file << "\nEQUAL " << lhs << " " << rhs;
    }

    return conjectures;
}

inline float get_entropy (const std::vector<float> & probs)
{
    float entropy = 0;
    for (float p : probs) {
        if (p > 0) {
            entropy += p * logf(p);
        }
    }
    return entropy;
}

void weigh_conjecture (
        Structure & structure,
        const std::unordered_map<std::string, float> & language,
        Ob lhs,
        Ob rhs,
        const std::string & equation,
        const char * conjectures_file)
{
    pid_t child = fork();
    POMAGMA_ASSERT(child != -1, "fork failed");

    if (child == 0) {
        POMAGMA_INFO("Assuming " << equation);
        Carrier & carrier = structure.carrier();
        carrier.set_merge_callback(schedule_merge);
        Ob dep = std::max(lhs, rhs);
        Ob rep = std::min(lhs, rhs);
        carrier.merge(dep, rep);
        process_mergers(structure.signature());
        size_t nullary_count = structure.signature().nullary_functions().size();
        bool consistent = carrier.item_count() >= nullary_count;
        if (consistent) {
            compact(structure);

            POMAGMA_DEBUG("measuring entropy");
            detail::Router router(structure, language);
            const std::vector<float> probs = router.measure_probs(0.01f);
            float entropy = get_entropy(probs);
            std::ofstream file(conjectures_file, std::ios::app);
            POMAGMA_ASSERT(file, "failed to open " << conjectures_file);
            file << "\n" << entropy << " " << equation;
        }
        _exit(0);
    } else {
        int status;
        wait(&status);
        POMAGMA_ASSERT(status == 0, "child process failed");
    }
}

void conjecture_deep (
        Structure & structure,
        const std::unordered_map<std::string, float> & language,
        const std::vector<std::string> & routes,
        const std::vector<std::pair<Ob, Ob>> & shallow_conjectures,
        const char * conjectures_file)
{
    POMAGMA_INFO("Generating deep conjectures");
    // TODO omit binary relations
    //structure.signature().binary_relations().clear();

    POMAGMA_DEBUG("writing conjectures to " << conjectures_file);
    {
        std::ofstream file(conjectures_file, std::ios::out);
        POMAGMA_ASSERT(file, "failed to open " << conjectures_file);
        file << "# deep conjectures generated by pomagma";
    }
    for (auto pair : shallow_conjectures) {
        const Ob lhs = pair.first;
        const Ob rhs = pair.second;
        std::string equation = "EQUAL " + routes[lhs] + " " + routes[rhs];
        weigh_conjecture(
            structure,
            language,
            lhs,
            rhs,
            equation,
            conjectures_file);
    }
}

} // namespace detail

void conjecture_shallow (
        Structure & structure,
        const char * language_file,
        const char * conjectures_file,
        size_t max_count)
{
    const auto language = load_language(language_file);
    detail::Router router(structure, language);
    const std::vector<float> probs = router.measure_probs();
    std::vector<std::string> routes = router.find_routes();
    detail::conjecture(structure, probs, routes, conjectures_file, max_count);
}

void conjecture_deep (
        Structure & structure,
        const char * language_file,
        const char * conjectures_file,
        size_t max_count)
{
    const auto language = load_language(language_file);
    detail::Router router(structure, language);
    const std::vector<float> probs = router.measure_probs();
    std::vector<std::string> routes = router.find_routes();
    const auto conjectures = detail::conjecture(
        structure,
        probs,
        routes,
        conjectures_file,
        max_count);
    detail::conjecture_deep(
        structure,
        language,
        routes,
        conjectures,
        conjectures_file);
}

} // namespace pomagma
