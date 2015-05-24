#pragma once

#include <vector>
#include <unordered_map>
#include <pomagma/analyst/approximator.hpp>
#include <pomagma/analyst/corpus.hpp>
#include <pomagma/platform/threading.hpp>

namespace pomagma
{

class Propagator
{
public:

    Propagator (Approximator & approximator) : m_approximator(approximator) {}

    struct AsyncValidity
    {
        Approximator::Validity validity;
        bool pending;
    };

    std::vector<AsyncValidity> validate (
            const std::vector<Corpus::LineOf<const Corpus::Term *>> & lines,
            Corpus::Linker & linker);

private:

    Approximator & m_approximator;

    enum Parity {UPPER, LOWER, NUPPER, NLOWER};
    struct Task
    {
        const Corpus::Term * term;
        Parity parity;
    };

    class Bounds : noncopyable
    {
    public:

        Bounds (const DenseSet * defaults[4])
        {
            for (size_t i = 0; i < 4; ++i) {
                m_defaults[i] = defaults[i];
            }
        }

        void reserve (const Corpus::Term * term)
        {
            m_index.insert({term, m_index.size()});
            for (size_t i = 0; i < 4; ++i) {
                m_bounds[i].resize(m_index.size(), defaults[i]);
            }
        }

        const HashedSet * get (
                Parity parity,
                const Corpus::Term * term) const
        {
            return m_bounds[parity][index(term)];
        }

        // returns true if value changed
        bool replace (
                Parity parity,
                const Corpus::Term * term,
                const HashedSet * bound)
        {
            auto & value = m_bounds[parity][index(term)];
            bool changed = (value != term);
            value = term;
            return changed;
        }

    private:

        size_t index (const Corpus::Term * term) const
        {
            auto i = m_index.find(term);
            POMAGMA_ASSERT1(i != m_index.end(), "index not initialized");
            return i->second;
        }

        std::unordered_map<const Term *, size_t> m_index;
        std::vector<const HashedSet *> m_bounds[4];
        const DenseSet * m_defaults[4];
    };

    // Version 1: state in its own object
    const DenseSet * m_unknown[4];
    Bounds m_bounds;

    // Version 2: state at class level
    // struct State { const HashedSet * bounds[4]; Ob ob; }
    // State m_default;
    // std::unordered_map<const Term *, State> m_states;
};

} // namespace pomagma
