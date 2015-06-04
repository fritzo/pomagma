#pragma once

#include <pomagma/util/util.hpp>
#include <pomagma/atlas/messages.pb.h>

namespace pomagma {

// simple delta encoding
inline void compress_sparse_map (protobuf::SparseMap & chunk)
{
    POMAGMA_ASSERT_EQ(chunk.key_size(), chunk.val_size());
    int prev_key = 0;
    int prev_val = 0;
    for (size_t i = 0, count = chunk.key_size(); i < count; ++i) {
        int key = chunk.key(i);
        int val = chunk.val(i);
        POMAGMA_ASSERT1(key > prev_key, "keys are not increasing")
        chunk.add_key_diff_minus_one(key - prev_key - 1);
        chunk.add_val_diff(val - prev_val);
        prev_key = key;
        prev_val = val;
    }
    chunk.clear_key();
    chunk.clear_val();
}

// simple delta decoding
inline void decompress_sparse_map (protobuf::SparseMap & chunk)
{
    POMAGMA_ASSERT_EQ(chunk.key_diff_minus_one_size(), chunk.val_diff_size());
    int key = 0;
    int val = 0;
    for (size_t i = 0, count = chunk.val_diff_size(); i < count; ++i) {
        chunk.add_key(key += chunk.key_diff_minus_one(i) + 1);
        chunk.add_val(val += chunk.val_diff(i));
    }
    chunk.clear_key_diff_minus_one();
    chunk.clear_val_diff();
}

} // namespace pomagma
