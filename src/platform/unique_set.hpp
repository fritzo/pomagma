#pragma once

#include <pomagma/platform/util.hpp>
#include <pomagma/platform/hash_map.hpp>
#include <unordered_set>

namespace pomagma
{

/// Store a set of objects so they can be hashed on location rather than value.
template<
    class Value,
    class Hash = std::hash<Value>>
class UniqueSet : noncopyable
{
    struct EqualPtr
    {
        bool operator() (const Value * x, const Value * y) const
        {
            return (* x) == (* y);
        }
    };

    struct HashPtr
    {
        Hash hash;
        uint64_t operator() (const Value * value) const
        {
            return hash(* value);
        }
    };

public:

    ~UniqueSet ()
    {
        for (auto value : m_values) {
            delete value;
        }
    }

    const Value * insert (const Value * key)
    {
        auto pair = m_values.insert(key);
        return * pair.first;
    }

    const Value * insert_or_delete (const Value * key)
    {
        auto pair = m_values.insert(key);
        if (not pair.second) {
            delete key;
        }
        return * pair.first;
    }

private:

    std::unordered_set<const Value *, HashPtr, EqualPtr> m_values;
};

} // namespace pomagma
