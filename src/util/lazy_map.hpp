#pragma once

#include <functional>
#include <mutex>
#include <pomagma/util/worker_pool.hpp>
#include <unordered_map>

namespace pomagma {

// Key and Value should be small structs.
// Value must be default constructible, equality comparable,
// and have an identified null_value.
// Function must never return null_value.
template<
    class Key,
    class Value,
    Value null_value = 0,
    class Hash = std::hash<Key>>
class LazyMap : noncopyable
{
public:

    LazyMap (
            size_t thread_count,
            std::function<Value (const Key &)> && function) :
        m_function(function),
        m_worker_pool(thread_count)
    {}

    // Immediately returns function(key) if ready or null_value if pending.
    // Guarantees that repeated calls with fixed key will eventually be ready.
    Value try_find (const Key & key)
    {
        {
            std::unique_lock<std::mutex> lock(m_mutex);
            auto inserted = m_cache.insert({key, null_value});
            if (likely(not inserted.second)) {
                return inserted.first->second;  // may be null_value
            }
        }
        m_worker_pool.schedule([this, key]{
            Value value = m_function(key);  // assumes this is expensive
            POMAGMA_ASSERT(value != null_value, "function returned null_value");
            std::unique_lock<std::mutex> lock(m_mutex);
            auto i = m_cache.find(key);
            POMAGMA_ASSERT1(i != m_cache.end(), "missing key");
            POMAGMA_ASSERT1(i->second == null_value, "value already added");
            i->second = std::move(value);
        });
        return null_value;
    }

    // Use this to load precomputed function values.
    void unsafe_insert (const Key & key, const Value & value)
    {
        POMAGMA_ASSERT(value != null_value, "inserted null_value");
        // POMAGMA_ASSERT5(m_function(key) == value, "miscomputed value");
        auto inserted = m_cache.insert({key, value});
        if (not inserted.second and inserted.first->second != null_value) {
            POMAGMA_ASSERT(value == inserted.first->second, "value conflict");
        }
    }

private:

    std::mutex m_mutex;
    std::unordered_map<Key, Value, Hash> m_cache;
    std::function<Value (const Key &)> m_function;
    mutable WorkerPool m_worker_pool;
};

} // namespace pomagma
