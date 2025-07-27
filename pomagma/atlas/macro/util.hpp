#pragma once

#include <pomagma/atlas/obs.hpp>
#include <pomagma/util/util.hpp>

#define POMAGMA_USE_SPARSE_HASH 0

#if POMAGMA_USE_SPARSE_HASH == 1
#include <google/sparse_hash_map>
#elif POMAGMA_USE_SPARSE_HASH == 2
#include <google/dense_hash_map>
#else  // POMAGMA_USE_SPARSE_HASH == 0
#include <unordered_map>
#endif  // POMAGMA_USE_SPARSE_HASH

#define POMAGMA_HAS_INVERSE_INDEX (0)

namespace pomagma {

namespace sequential {}
using namespace sequential;

// TODO switch to absl::flat_hash_map and absl::flat_hash_set
#if POMAGMA_USE_SPARSE_HASH == 1

struct ObPairMap : google::sparse_hash_map<std::pair<Ob, Ob>, Ob, ObPairHash> {
    ObPairMap() { set_deleted_key({0, 0}); }
};

#elif POMAGMA_USE_SPARSE_HASH == 2

struct ObPairMap : google::dense_hash_map<std::pair<Ob, Ob>, Ob, ObPairHash> {
    ObPairMap() {
        set_empty_key({0, 0});
        set_deleted_key({0, 1});
    }
};

#else  // POMAGMA_USE_SPARSE_HASH == 0

typedef std::unordered_map<std::pair<Ob, Ob>, Ob, ObPairHash> ObPairMap;

#endif  // POMAGMA_USE_SPARSE_HASH

}  // namespace pomagma
