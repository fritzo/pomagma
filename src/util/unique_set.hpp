#pragma once

#include <pomagma/util/util.hpp>
#include <pomagma/util/hash_map.hpp>
#include <unordered_set>
#include <tbb/concurrent_unordered_set.h>

namespace pomagma {

namespace detail {

template <class Value, class Hash, class Equal, bool concurrent>
struct unordered_set;

template <class Value, class Hash, class Equal>
struct unordered_set<Value, Hash, Equal, true> {
    typedef typename tbb::concurrent_unordered_set<Value, Hash, Equal> t;
};

template <class Value, class Hash, class Equal>
struct unordered_set<Value, Hash, Equal, false> {
    typedef typename std::unordered_set<Value, Hash, Equal> t;
};

}  // namespace detail

/// Store a set of objects so they can be hashed on location rather than value.
template <class Value, class Hash = std::hash<Value>, bool concurrent = true>
class UniqueSet : noncopyable {
    struct EqualPtr {
        bool operator()(const Value *x, const Value *y) const {
            return (*x) == (*y);
        }
    };

    struct HashPtr {
        Hash hash;
        uint64_t operator()(const Value *value) const { return hash(*value); }
    };

   public:
    ~UniqueSet() {
        for (auto value : m_values) {
            delete value;
        }
    }

    const Value *insert(const Value *key) {
        auto pair = m_values.insert(key);
        return *pair.first;
    }

    const Value *insert_or_delete(const Value *key) {
        auto pair = m_values.insert(key);
        if (not pair.second) {
            delete key;
        }
        return *pair.first;
    }

   private:
    typename detail::unordered_set<const Value *, HashPtr, EqualPtr,
                                   concurrent>::t m_values;
};

}  // namespace pomagma
