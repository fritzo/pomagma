#pragma once

#include <cstdint>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace util {
uint64_t Fingerprint(uint64_t key);
}

namespace pomagma {
namespace reducer {

typedef int32_t Ob;  // 0 is null; positive are terms; negative are variables.
typedef std::pair<Ob, Ob> ObPair;
typedef std::unordered_set<Ob> ObSet;

struct ObPairHash {
    size_t operator()(const std::pair<Ob, Ob>& x) const {
        static_assert(sizeof(x) == sizeof(size_t), "invalid ob size");
        return util::Fingerprint(*reinterpret_cast<const size_t*>(&x));
    }
};

typedef std::unordered_set<ObPair, ObPairHash> ObPairSet;

}  // namespace reducer
}  // namespace pomagma
