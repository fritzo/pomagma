#pragma once

#include <pomagma/atlas/structure.pb.h>

#include <pomagma/io/blobstore.hpp>
#include <pomagma/io/protobuf.hpp>
#include <pomagma/util/util.hpp>
#include <google/protobuf/stubs/common.h>

namespace pomagma {
namespace protobuf {

using namespace atlas::protobuf;

// Template function to initialize protobuf with static linking support
// This ensures descriptor initialization happens properly with vcpkg static linking
template<typename T>
inline void init_protobuf() {
    // Initialize protobuf library
    GOOGLE_PROTOBUF_VERIFY_VERSION;
    
    // Force descriptor initialization by accessing the descriptor
    // This ensures static initialization happens with static linking
    const auto* descriptor = T::descriptor();
    POMAGMA_ASSERT(descriptor != nullptr, "Failed to initialize protobuf descriptors");
}

inline void delta_compress(ObMap& map) {
    POMAGMA_ASSERT_EQ(map.key_size(), map.val_size());
    POMAGMA_ASSERT_EQ(0, map.key_diff_minus_one_size());
    POMAGMA_ASSERT_EQ(0, map.val_diff_size());
    int prev_key = 0;
    int prev_val = 0;
    for (size_t i = 0, count = map.key_size(); i < count; ++i) {
        int key = map.key(i);
        int val = map.val(i);
        POMAGMA_ASSERT1(key > prev_key, "keys are not increasing")
        map.add_key_diff_minus_one(key - prev_key - 1);
        map.add_val_diff(val - prev_val);
        prev_key = key;
        prev_val = val;
    }
    map.clear_key();
    map.clear_val();
}

// this leaves uncompressed data uncompressed
inline void delta_decompress(ObMap& map) {
    POMAGMA_ASSERT_EQ(map.key_diff_minus_one_size(), map.val_diff_size());
    POMAGMA_ASSERT_EQ(map.key_size(), map.val_size());
    int key = 0;
    int val = 0;
    for (size_t i = 0, count = map.val_diff_size(); i < count; ++i) {
        map.add_key(key += map.key_diff_minus_one(i) + 1);
        map.add_val(val += map.val_diff(i));
    }
    map.clear_key_diff_minus_one();
    map.clear_val_diff();
}

template <class DenseSet>
inline void dump(const DenseSet& set, ObSet& message) {
    const size_t byte_count = set.max_item() / 8 + 1;
    message.set_dense(set.raw_data(), byte_count);
}

template <class DenseSet>
inline void load(DenseSet& set, const ObSet& message) {
    POMAGMA_ASSERT_LE(message.dense().size(), set.data_size_bytes());
    POMAGMA_ASSERT1(set.empty(), "DenseSet not empty before load");
    memcpy(set.raw_data(), message.dense().data(), message.dense().size());
    if (POMAGMA_DEBUG_LEVEL >= 3) {
        set.validate();
    }
}

}  // namespace protobuf
}  // namespace pomagma
