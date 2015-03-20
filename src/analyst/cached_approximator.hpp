#pragma once

#include <pomagma/analyst/approximate.hpp>
#include <pomagma/platform/hash_map.hpp>
#include <pomagma/platform/async_map.hpp>
#include <pomagma/platform/unique_set.hpp>
#include <tbb/concurrent_unordered_map.h>

namespace pomagma
{

// TODO profile hash conflict rate
struct HashedApproximation
{
private:
public:
    const Approximation approx;
    const uint64_t hash;

    HashedApproximation (Approximation && a)
        : approx(std::move(a)),
          hash(compute_hash(approx))
    {
    }
    HashedApproximation (const HashedApproximation &) = delete;

    bool operator== (const HashedApproximation & other) const
    {
        return hash == other.hash and approx == other.approx;
    }
    bool operator!= (const HashedApproximation & other) const
    {
        return not operator==(other);
    }

    struct Hash
    {
        uint64_t operator() (const HashedApproximation & x) const
        {
            return x.hash;
        }
    };

private:

    static uint64_t compute_hash (const Approximation & approx);
};

class CachedApproximator : noncopyable
{
public:

    struct Term
    {
        enum Arity {
            OB,
            HOLE,
            NULLARY_FUNCTION,
            INJECTIVE_FUNCTION,
            BINARY_FUNCTION,
            SYMMETRIC_FUNCTION,
            UNARY_RELATION,
            BINARY_RELATION
        };

        struct Hash
        {
            std::hash<std::string> hash_string;
            std::hash<const HashedApproximation *> hash_pointer;

            uint64_t operator() (const Term & x) const
            {
                FNV_hash::HashState state;
                state.add(x.arity);
                state.add(hash_string(x.name));
                state.add(hash_pointer(x.arg0));
                state.add(hash_pointer(x.arg1));
                state.add(x.ob);
                return state.get();
            }
        };

        bool operator== (const Term & o) const
        {
            return arity == o.arity
               and name == o.name
               and arg0 == o.arg0
               and arg1 == o.arg1
               and ob == o.ob;
        }
        bool operator!= (const Term & o) const { return not operator==(o); }

        Arity arity;
        std::string name;
        const HashedApproximation * arg0;
        const HashedApproximation * arg1;
        Ob ob;
    };

private:

    typedef AsyncMap<const Term *, HashedApproximation> Cache;

    struct Task
    {
        const Term * term;
        Cache::Callback callback;
    };

    struct Processor
    {
        CachedApproximator & approximator;

        void operator() (Task & task)
        {
            task.callback(
                approximator.m_approximations.insert_or_delete(
                    new HashedApproximation(
                        approximator.compute(
                            task.term))));
        }
    };

    struct AsyncFunction
    {
        WorkerPool<Task, Processor> & pool;

        void operator() (const Term * term, Cache::Callback callback)
        {
            pool.schedule(Task({term, callback}));
        }
    };

public:

    CachedApproximator (
            Approximator & approximator,
            size_t thread_count)
        : m_approximator(approximator),
          m_processor({* this}),
          m_pool(m_processor, thread_count),
          m_function({m_pool}),
          m_cache(std::bind(&AsyncFunction::operator(), & m_function, _1, _2))
    {
    }

    void find_async (
            const Term & term,
            Cache::Callback callback)
    {
        const Term * key = m_terms.insert_or_delete(new Term(term));
        m_cache.find_async(key, callback);
    }

private:

    Approximation compute (const Term * term)
    {
        const auto & name = term->name;
        auto * arg0 = term->arg0;
        auto * arg1 = term->arg1;

        switch (term->arity) {
            case Term::OB:
                return m_approximator.known(term->ob);

            case Term::HOLE:
                return m_approximator.unknown();

            case Term::NULLARY_FUNCTION:
                return m_approximator.find(name);

            case Term::INJECTIVE_FUNCTION:
            case Term::UNARY_RELATION:
                return m_approximator.find(name, arg0->approx);

            case Term::BINARY_FUNCTION:
            case Term::SYMMETRIC_FUNCTION:
            case Term::BINARY_RELATION:
                return m_approximator.find(name, arg0->approx, arg1->approx);
        }

        POMAGMA_ERROR("unreachable");
    }

    Approximator & m_approximator;
    Processor m_processor;
    WorkerPool<Task, Processor> m_pool;
    AsyncFunction m_function;
    UniqueSet<HashedApproximation, HashedApproximation::Hash> m_approximations;
    UniqueSet<Term, Term::Hash> m_terms;
    Cache m_cache;
};

} // namespace pomagma
