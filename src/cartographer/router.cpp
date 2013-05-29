#include "router.hpp"
#include "carrier.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"

namespace pomagma
{

inline Router::TypeId Router::new_type (
        Router::Arity arity,
        const std::string & name)
{
    auto i = m_language.find(name);
    float prob = i == m_language.end() ? 0.f : i->second;
    m_types.push_back(SegmentType(arity, name, prob));
    return m_types.size() - 1;
}

inline Range<Router::Iterator> Router::iter_val (Ob val) const
{
    size_t begin = m_value_index[val - 1];
    size_t end = m_value_index[val] + 1;
    return range(m_segments.begin() + begin, m_segments.begin() + end);
}

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

        // The following cannot be mixed: openmp, gc, fork.
        // see http://bisqwit.iki.fi/story/howto/openmp/#OpenmpAndFork
        //# pragma omp parallel for schedule(dynamic, 1)
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
                //#pragma omp atomic
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

        //#pragma omp parallel for schedule(dynamic, 1)
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
                //#pragma omp atomic
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

} // namespace pomagma
