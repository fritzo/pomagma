#pragma once

#include <pomagma/analyst/approximate.hpp>
#include <pomagma/platform/hash_map.hpp>
#include <pomagma/platform/worker_pool.hpp>
#include <tbb/concurrent_unordered_map.h>

namespace pomagma
{

struct HashedApproximation
{
    const uint64_t hash;
    const Approximation approx;

    HashedApproximation (Approximation && a)
        : hash(compute_hash(a)),
          approx(std::move(a))
    {
    }
    HashedApproximation (const HashedApproximation &) = delete;

    bool operator== (const HashedApproximation & other) const
    {
        return hash == other.hash and approx == other.approx;
    }

private:

    static uint64_t compute_hash (const Approximation & approx);
};


// TODO garbage collect
// TODO make cache persistent
// TODO profile hash conflict rate

class CachedApproximator : noncopyable
{

    struct Key
    {
        std::string name;
        const HashedApproximation * arg0;
        const HashedApproximation * arg1;

        struct Equal
        {
            template<class T>
            bool maybe (const T * x, const T * y) const
            {
                return x ? (y and *x == *y) : not y;
            }

            bool operator() (const Key & x, const Key & y) const
            {
                return x.name == y.name
                   and maybe(x.arg0, y.arg0)
                   and maybe(x.arg1, y.arg1);
            }
        };

        struct Hash
        {
            std::hash<std::string> hash_string;

            uint64_t operator() (const Key & key) const
            {
                FNV_hash::HashState state;
                state.add(hash_string(key.name));
                state.add(key.arg0 ? key.arg0->hash : 0);
                state.add(key.arg1 ? key.arg1->hash : 0);
                return state.get();
            }
        };
    };

    typedef HashedApproximation * Value;

    typedef tbb::concurrent_unordered_map<Key, Value, Key::Hash, Key::Equal>
        Cache;

    struct Task
    {
        Cache::iterator i;
        CachedApproximator * approximator;

        void operator() () { approximator->compute_and_store(i); }
    };

public:

    CachedApproximator (
            Approximator & approximator,
            size_t thread_count = 1)
        : m_approximator(approximator),
          m_pool(thread_count)
    {
    }

    ~CachedApproximator ()
    {
        m_pool.wait();
        for (auto i : m_cache) {
            delete i.second;
        }
    }

    HashedApproximation * find (
            const std::string & name,
            const HashedApproximation * arg0 = nullptr,
            const HashedApproximation * arg1 = nullptr)
    {
        Key key = {name, arg0, arg1};
        return find(key);
    }

private:

    HashedApproximation * find (const Key & key)
    {
        auto pair = m_cache.insert(std::make_pair(key, nullptr));
        auto & i = pair.first;
        bool inserted = pair.second;
        if (inserted) {
            Task task = {i, this};
            m_pool.schedule(task);
        }
        return i->second;
    }

    Approximation compute (const Key & key)
    {
        const auto & name = key.name;
        auto * arg0 = key.arg0;
        auto * arg1 = key.arg1;

        if (key.arg1) {
            return m_approximator.find(name, arg0->approx, arg1->approx);
        } else if (key.arg0) {
            return m_approximator.find(name, arg0->approx);
        } else {
            return m_approximator.find(name);
        }
    }

    void compute_and_store (Cache::iterator & i)
    {
        const Key & key = i->first;
        Value & value = i->second;
        value = new HashedApproximation(compute(key));
    }

    Approximator & m_approximator;
    Cache m_cache;
    WorkerPool<Task> m_pool;
};

} // namespace pomagma
