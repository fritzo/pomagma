#pragma once

#include <pomagma/analyst/approximate.hpp>
#include <pomagma/analyst/cached_approximator.hpp>
#include <pomagma/analyst/corpus.hpp>
#include <pomagma/platform/async_map.hpp>
#include <pomagma/platform/unique_set.hpp>
#include <set>
#include <thread>
#include <mutex>

namespace pomagma
{

class Validator : noncopyable
{
    typedef AsyncMap<const Corpus::Term *, HashedApproximation> Cache;

    class Task
    {
    public:

        Task (
                Validator & validator,
                const Corpus::Term * term,
                Cache::Callback callback)
            : m_validator(validator),
              m_term(term),
              m_callback(callback),
              m_state(term->arg1 ? 3 : term->arg0 ? 2 : 1)
        {
            if (term->arg0) {
                m_validator.m_cache.find_async(
                    term->arg0,
                    std::bind(&Task::operator(), this, _1));
            }
            if (term->arg1) {
                m_validator.m_cache.find_async(
                    term->arg1,
                    std::bind(&Task::operator(), this, _1));
            }
            operator()(nullptr);
        }

        void operator() (const HashedApproximation *)
        {
            if (--m_state == 0) {
                if (m_term->arity == Corpus::Term::VARIABLE) {
                    TODO("deal with variables")
                } else {
                    m_validator.m_cached_approximator.find_async(
                        m_validator.convert(m_term),
                        m_callback);
                    delete this;
                }
            }
        }

    private:

        Validator & m_validator;
        const Corpus::Term * m_term;
        Cache::Callback m_callback;
        std::atomic<int> m_state;
    };

    class AsyncFunction : noncopyable
    {
    public:

        AsyncFunction (Validator * validator)
            : m_validator(* validator)
        {
        }

        void operator() (const Corpus::Term * term, Cache::Callback callback)
        {
            new Task(m_validator, term, callback);
        }

    private:

        Validator & m_validator;
    };

public:

    Validator (
            Approximator & approximator,
            size_t thread_count = 1)
        : m_approximator(approximator),
          m_cached_approximator(approximator),
          m_function(this),
          m_cache(std::bind(&AsyncFunction::operator(), & m_function, _1, _2))
    {
        POMAGMA_ASSERT_LT(0, thread_count);
    }

    std::vector<Approximator::Validity> validate (
            const std::vector<Corpus::LineOf<const Corpus::Term *>> & lines);

    Approximator::Validity is_valid (const Corpus::Term * term)
    {
        if (auto approx = m_cache.find(term)) {
            return m_approximator.is_valid(approx->approx);
        } else {
            return Approximator::Validity::unknown();
        }
    }

private:

    const HashedApproximation * find (const Corpus::Term * term)
    {
        return term ? m_cache.find(term) : nullptr;
    }

    CachedApproximator::Term convert (const Corpus::Term * term)
    {

#define POMAGMA_ASSERT_ARITY(arity)\
        static_assert(\
            int(Corpus::Term::arity) == int(CachedApproximator::Term::arity),\
            "arity mismatch: " #arity);
        POMAGMA_ASSERT_ARITY(OB)
        POMAGMA_ASSERT_ARITY(HOLE)
        POMAGMA_ASSERT_ARITY(NULLARY_FUNCTION)
        POMAGMA_ASSERT_ARITY(INJECTIVE_FUNCTION)
        POMAGMA_ASSERT_ARITY(BINARY_FUNCTION)
        POMAGMA_ASSERT_ARITY(SYMMETRIC_FUNCTION)
        POMAGMA_ASSERT_ARITY(BINARY_RELATION)
#undef POMAGMA_ASSERT_ARITY

        CachedApproximator::Term hashed = {
            static_cast<CachedApproximator::Term::Arity>(term->arity),
            term->name,
            m_cache.find(term->arg0),
            m_cache.find(term->arg1),
            term->ob
        };

        return hashed;
    }

    Approximator & m_approximator;
    CachedApproximator m_cached_approximator;
    AsyncFunction m_function;
    Cache m_cache;

    class Linker;
};

} // namespace pomagma
