#pragma once

#include <pomagma/analyst/approximate.hpp>
#include <pomagma/platform/hash_map.hpp>

namespace pomagma
{

struct HashedApproximation
{
    const Approximation approx;
    const uint64_t hash;

    HashedApproximation (Approximation && a)
        : approx(std::move(a)),
          hash(compute_hash(a))
    {
    }
    HashedApproximation (const HashedApproximation &) = delete;

    bool operator== (const HashedApproximation & other) const
    {
        return hash == other.hash and approx == other.approx;
    }
    bool operator!= (const HashedApproximation & other) const
    {
        return hash != other.hash or approx != other.approx;
    }

private:

    static uint64_t compute_hash (const Approximation & approx);
};

class CachedApproximator : noncopyable
{
public:

    CachedApproximator (Approximator & approximator)
        : m_approximator(approximator)
    {
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

    struct Key
    {
        const std::string name;
        const HashedApproximation * const arg0;
        const HashedApproximation * const arg1;

        struct Equal
        {
            bool operator() (const Key & x, const Key & y) const
            {
                if (x.name != y.name) return false;
                if (x.arg0) {
                    if (!y.arg0 or *x.arg0 != *y.arg0) return false;
                } else {
                    if (y.arg0) return false;
                }
                if (x.arg1) {
                    if (!y.arg1 or *x.arg1 != *y.arg1) return false;
                } else {
                    if (y.arg1) return false;
                }
                return true;
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

    HashedApproximation * find (const Key & key)
    {
        auto i = m_cache.find(key);
        if (i == m_cache.end()) {
            return m_cache[key] = nullptr;
            // TODO enqueue work
        } else {
            return i->second;
        }
    }

    Approximator & m_approximator;
    std::unordered_map<Key, Value, Key::Hash, Key::Equal> m_cache;
};

} // namespace pomagma
