#pragma once

#include <pomagma/platform/util.hpp>
#include <pomagma/platform/worker_pool.hpp>
#include <tbb/concurrent_unordered_map.h>
#include <unordered_map>
#include <mutex>

namespace pomagma
{

using namespace std::placeholders;

template<class Key, class Value>
class AsyncMap : noncopyable
{
public:

    typedef std::function<void(const Value *)> Callback;
    typedef std::function<void(Key, Callback)> AsyncFunction;

    AsyncMap (AsyncFunction function)
        : m_function(function)
    {
    }

    ~AsyncMap ()
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        POMAGMA_ASSERT_EQ(m_callbacks.size(), 0);
        for (auto v : m_values) {
            delete v.second;
        }
    }

    const Value * find (const Key & key)
    {
        auto pair = m_values.insert(std::make_pair(key, nullptr));
        auto & value = pair.first->second;
        bool inserted = pair.second;
        if (unlikely(inserted)) {
            {
                std::lock_guard<std::mutex> lock(m_mutex);
                callbacks_locked(key);
            }
            m_function(key, std::bind(&AsyncMap::store, this, key, _1));
        }
        return value;
    }

    void find_async (const Key & key, Callback callback)
    {
        auto pair = m_values.insert(std::make_pair(key, nullptr));
        auto & value = pair.first->second;
        bool inserted = pair.second;
        if (likely(not inserted)) {
            if (likely(value)) {
                callback(value);
            } else {
                bool called = false;
                {
                    std::lock_guard<std::mutex> lock(m_mutex);
                    if (likely(not value)) {
                        callbacks_locked(key).push_back(callback);
                        called = true;
                    }
                }
                if (not called) {
                    callback(value);
                }
            }
        } else {
            {
                std::lock_guard<std::mutex> lock(m_mutex);
                callbacks_locked(key).push_back(callback);
            }
            m_function(key, std::bind(&AsyncMap::store, this, key, _1));
        }
    }

private:

    std::vector<Callback> & callbacks_locked (Key key)
    {
        auto pair = m_callbacks.insert(std::make_pair(key, nullptr));
        auto & callbacks = pair.first->second;
        bool inserted = pair.second;
        if (inserted) {
            callbacks = new std::vector<Callback>();
        }
        return * callbacks;
    }

    void store (Key key, const Value * value)
    {
        POMAGMA_ASSERT(value, "tried to store null value");
        std::vector<Callback> * callbacks = nullptr;
        {
            std::lock_guard<std::mutex> lock(m_mutex);

            auto v = m_values.find(key);
            POMAGMA_ASSERT1(v != m_values.end(), "value not found");
            v->second = value;

            auto c = m_callbacks.find(key);
            POMAGMA_ASSERT1(c != m_callbacks.end(), "callbacks not found");
            callbacks = c->second;
            m_callbacks.erase(c);
        }
        for (auto callback : * callbacks) {
            callback(value);
        }
        delete callbacks;
    }

    AsyncFunction m_function;
    tbb::concurrent_unordered_map<Key, const Value *> m_values;
    std::unordered_map<Key, std::vector<Callback> *> m_callbacks;
    std::mutex m_mutex;
};

} // namespace pomagma
