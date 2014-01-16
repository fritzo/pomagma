#pragma once

#include "util.hpp"
#include "structure.hpp"
#include <pomagma/platform/sequential/dense_set.hpp>
#include <unordered_map>

namespace pomagma
{

class Router
{
public:

    Router (
        const Signature & signature,
        const std::unordered_map<std::string, float> & language);

    const std::unordered_map<std::string, float> & get_language () const
    {
        return m_language;
    }

    DenseSet find_defined () const;
    std::vector<float> measure_probs (float reltol = 0.1) const;
    std::vector<std::string> find_routes () const;
    void fit_language (
            const std::unordered_map<std::string, size_t> & symbol_counts,
            const std::unordered_map<Ob, size_t> & ob_counts,
            float reltol = 0.1);

private:

    void update_probs (
            std::vector<float> & probs,
            float reltol = 0.1) const;
    void update_weights (
            const std::vector<float> & probs,
            const std::unordered_map<std::string, size_t> & symbol_counts,
            const std::unordered_map<Ob, size_t> & ob_counts,
            std::vector<float> & symbol_weights,
            std::vector<float> & ob_weights,
            float reltol = 0.1) const;

    bool defines (const DenseSet & defined, Ob ob) const;

    enum Arity { NULLARY, INJECTIVE, BINARY };

    struct SegmentType
    {
        Arity arity;
        std::string name;
        float prob;

        SegmentType () {}
        SegmentType (Arity a, const std::string & n, float p)
            : arity(a), name(n), prob(p)
        {}
    };

    typedef uint32_t TypeId;
    TypeId new_type (Arity arity, const std::string & name);

    struct Segment
    {
        TypeId type;
        Ob val;
        Ob arg1;
        Ob arg2;

        Segment () {}
        Segment (TypeId t, Ob v, Ob a1=0, Ob a2=0)
            : type(t), val(v), arg1(a1), arg2(a2)
        {}
    };

    typedef std::vector<Segment>::const_iterator Iterator;
    Range<Iterator> iter_val (Ob val) const;

    float get_prob (
            const Segment & segment,
            const std::vector<float> & probs) const;
    void add_weight (
            float weight,
            const Segment & segment,
            std::vector<float> & symbol_weights,
            std::vector<float> & ob_weights) const;

    Carrier & m_carrier;
    std::unordered_map<std::string, float> m_language;
    std::vector<SegmentType> m_types;
    std::vector<Segment> m_segments;
    std::vector<size_t> m_value_index;
};

inline float get_entropy (const std::vector<float> & probs)
{
    float entropy = 0;
    for (float p : probs) {
        if (p > 0) {
            entropy -= p * logf(p);
        }
    }
    return entropy;
}

} // namespace pomagma
