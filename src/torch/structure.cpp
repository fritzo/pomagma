// PyTorch extension for pomagma operations.
// For reference, see:
// https://docs.pytorch.org/tutorials/advanced/cpp_custom_ops.html

#include "structure.hpp"

#include <pomagma/atlas/structure.pb.h>
#include <pomagma/third_party/farmhash/farmhash.h>

#include <pomagma/io/blobstore.hpp>
#include <pomagma/io/protobuf.hpp>

namespace pomagma {
namespace torch {

template <bool temperature>
at::Tensor binary_function_reduce_product(const at::Tensor& f_ptrs,
                                          const at::Tensor& f_args,
                                          const at::Tensor& lhs,
                                          const at::Tensor& rhs) {
    // Check shapes: f_ptrs [N+1], f_args [NNZ, 2], lhs [N], rhs [N]
    TORCH_CHECK(f_ptrs.dim() == 1);
    TORCH_CHECK(f_args.dim() == 2);
    TORCH_CHECK(lhs.dim() == 1);
    TORCH_CHECK(rhs.dim() == 1);
    const int64_t N = f_ptrs.size(0) - 1;
    const int64_t NNZ = f_args.size(0);
    TORCH_CHECK(lhs.size(0) == N);
    TORCH_CHECK(rhs.size(0) == N);

    // Check dtypes
    TORCH_CHECK(f_ptrs.dtype() == at::kInt);
    TORCH_CHECK(f_args.dtype() == at::kInt);
    TORCH_CHECK(lhs.dtype() == at::kFloat);
    TORCH_CHECK(rhs.dtype() == at::kFloat);

    // Check all tensors are on CPU
    TORCH_CHECK(f_ptrs.device().type() == at::DeviceType::CPU);
    TORCH_CHECK(f_args.device().type() == at::DeviceType::CPU);
    TORCH_CHECK(lhs.device().type() == at::DeviceType::CPU);
    TORCH_CHECK(rhs.device().type() == at::DeviceType::CPU);

    // Check all tensors are contiguous
    TORCH_CHECK(f_ptrs.is_contiguous());
    TORCH_CHECK(f_args.is_contiguous());
    TORCH_CHECK(lhs.is_contiguous());
    TORCH_CHECK(rhs.is_contiguous());

    const int32_t* f_ptrs_data = f_ptrs.data_ptr<int32_t>();
    TORCH_CHECK(f_ptrs_data[0] == 0);
    TORCH_CHECK(f_ptrs_data[N] == NNZ);
    const int32_t* f_args_data = f_args.data_ptr<int32_t>();
    const float* lhs_data = lhs.data_ptr<float>();
    const float* rhs_data = rhs.data_ptr<float>();

    at::Tensor out = at::empty_like(lhs);
    float* out_data = out.data_ptr<float>();

#pragma omp parallel for schedule(dynamic, 16)
    for (int64_t i = 0; i < N; i++) {
        float accum = 0;
        const int64_t begin = f_ptrs_data[i];
        const int64_t end = f_ptrs_data[i + 1];
        for (int64_t j = begin; j < end; j++) {
            const int64_t lhs_idx = f_args_data[j * 2];
            const int64_t rhs_idx = f_args_data[j * 2 + 1];
            const float val = lhs_data[lhs_idx] * rhs_data[rhs_idx];
            if constexpr (temperature) {
                accum += val;
            } else {
                accum = std::max(accum, val);
            }
        }
        out_data[i] = accum;
    }

    return out;
}

at::Tensor binary_function_distribute_product(const at::Tensor& f_ptrs,
                                              const at::Tensor& f_args,
                                              const at::Tensor& parent_counts,
                                              const at::Tensor& probs,
                                              double weight) {
    // Check shapes: f_ptrs [N+1], f_args [NNZ, 2], parent_counts [N], probs [N]
    TORCH_CHECK(f_ptrs.dim() == 1);
    TORCH_CHECK(f_args.dim() == 2);
    TORCH_CHECK(parent_counts.dim() == 1);
    TORCH_CHECK(probs.dim() == 1);
    const int64_t N = f_ptrs.size(0) - 1;
    const int64_t NNZ = f_args.size(0);
    TORCH_CHECK(parent_counts.size(0) == N);
    TORCH_CHECK(probs.size(0) == N);

    // Check dtypes
    TORCH_CHECK(f_ptrs.dtype() == at::kInt);
    TORCH_CHECK(f_args.dtype() == at::kInt);
    TORCH_CHECK(parent_counts.dtype() == at::kFloat);
    TORCH_CHECK(probs.dtype() == at::kFloat);

    // Check all tensors are on CPU
    TORCH_CHECK(f_ptrs.device().type() == at::DeviceType::CPU);
    TORCH_CHECK(f_args.device().type() == at::DeviceType::CPU);
    TORCH_CHECK(parent_counts.device().type() == at::DeviceType::CPU);
    TORCH_CHECK(probs.device().type() == at::DeviceType::CPU);

    // Check all tensors are contiguous
    TORCH_CHECK(f_ptrs.is_contiguous());
    TORCH_CHECK(f_args.is_contiguous());
    TORCH_CHECK(parent_counts.is_contiguous());
    TORCH_CHECK(probs.is_contiguous());

    const int32_t* f_ptrs_data = f_ptrs.data_ptr<int32_t>();
    TORCH_CHECK(f_ptrs_data[0] == 0);
    TORCH_CHECK(f_ptrs_data[N] == NNZ);
    const int32_t* f_args_data = f_args.data_ptr<int32_t>();
    const float* parent_counts_data = parent_counts.data_ptr<float>();
    const float* probs_data = probs.data_ptr<float>();

    at::Tensor out = at::zeros_like(probs);
    float* out_data = out.data_ptr<float>();

    const float eps = 1e-10f;  // Small epsilon to avoid division by zero
    const float weight_f = static_cast<float>(weight);

    // For each parent E-class, distribute its count to children
    for (int64_t v = 0; v < N; v++) {
        const float parent_count = parent_counts_data[v];
        if (parent_count == 0.0f) continue;

        const float parent_prob = probs_data[v];
        if (parent_prob <= eps)
            continue;  // Skip if parent has negligible probability

        // For each way to form v = f(l,r)
        const int64_t begin = f_ptrs_data[v];
        const int64_t end = f_ptrs_data[v + 1];
        for (int64_t j = begin; j < end; j++) {
            const int64_t l = f_args_data[j * 2];
            const int64_t r = f_args_data[j * 2 + 1];

            // Probability contribution of this decomposition f(l,r) = v
            const float decomp_prob = weight_f * probs_data[l] * probs_data[r];
            const float fraction = decomp_prob / parent_prob;
            const float contribution = parent_count * fraction;

// Add contributions to both children (atomic operations for thread safety)
#pragma omp atomic
            out_data[l] += contribution;
#pragma omp atomic
            out_data[r] += contribution;
        }
    }

    return out;
}

int64_t hash_pair(int64_t lhs, int64_t rhs) {
    // Pack two int64_t values into a 16-byte buffer for hashing
    uint64_t data[2] = {static_cast<uint64_t>(lhs), static_cast<uint64_t>(rhs)};

    // Use farmhash Fingerprint64 for consistent, portable hashing
    uint64_t hash_value =
        util::Fingerprint64(reinterpret_cast<const char*>(data), sizeof(data));

    // Convert back to signed int64_t for compatibility with Python
    return static_cast<int64_t>(hash_value);
}

template <typename MessageType, typename Func>
void visit_chunks(const MessageType& message, Func func) {
    // Visit the main message first
    func(message);

    // Visit chunks from blobs
    for (const auto& hexdigest : message.blobs()) {
        std::string blob_path = find_blob(hexdigest);
        protobuf::InFile blob_file(blob_path);
        MessageType chunk;
        blob_file.read(chunk);
        func(chunk);
        // Assert that chunks don't have nested blobs
        TORCH_CHECK(chunk.blobs().empty(),
                    "Chunk should not have nested blobs");
    }
}

std::tuple<std::vector<std::string>, std::vector<at::Tensor>> load_structure(
    const std::string& filename, bool relations) {
    std::vector<std::string> keys;
    std::vector<at::Tensor> tensors;

    // Read protobuf structure file using existing infrastructure
    // Note: filename should be a resolved blob path, not a blob reference
    atlas::protobuf::Structure proto_structure;
    protobuf::InFile file(filename);
    file.read(proto_structure);

    // Extract basic information
    int item_count = static_cast<int>(proto_structure.carrier().item_count());

    // Add item_count
    keys.emplace_back("item_count");
    tensors.emplace_back(at::tensor({item_count}, at::dtype(at::kInt)));

    // Add nullary functions
    for (const auto& proto_func : proto_structure.nullary_functions()) {
        std::string key = "nullary_functions." + proto_func.name();
        keys.emplace_back(key);
        tensors.emplace_back(at::tensor({static_cast<int>(proto_func.val())},
                                        at::dtype(at::kInt)));
    }

    // Helper lambda to delta decompress ObMap
    auto delta_decompress = [](const atlas::protobuf::ObMap& ob_map)
        -> std::pair<std::vector<uint32_t>, std::vector<uint32_t>> {
        std::vector<uint32_t> keys_out, vals_out;

        if (ob_map.key_diff_minus_one_size() == 0) {
            // Already uncompressed
            for (int i = 0; i < ob_map.key_size(); ++i) {
                keys_out.push_back(ob_map.key(i));
                vals_out.push_back(ob_map.val(i));
            }
        } else {
            // Delta compressed
            uint32_t key = 0, val = 0;
            for (int i = 0; i < ob_map.key_diff_minus_one_size(); ++i) {
                key += ob_map.key_diff_minus_one(i) + 1;
                val += ob_map.val_diff(i);
                keys_out.push_back(key);
                vals_out.push_back(val);
            }
        }
        return {keys_out, vals_out};
    };

    // Helper to process binary functions
    auto process_binary_function =
        [&](const atlas::protobuf::BinaryFunction& proto_func, bool symmetric) {
            std::string func_name = proto_func.name();

            // Count entries first (pass 1) using visit_chunks
            int func_entries = 0;
            std::vector<int> Vlr_counts(item_count + 1, 0);
            std::vector<int> Rvl_counts(item_count + 1, 0);
            std::vector<int> Lvr_counts(item_count + 1, 0);

            // Use visit_chunks to iterate over main message and all blob chunks
            visit_chunks(
                proto_func, [&](const atlas::protobuf::BinaryFunction& chunk) {
                    for (const auto& row : chunk.rows()) {
                        uint32_t lhs = row.lhs();
                        auto [rhs_keys, vals] = delta_decompress(row.rhs_val());

                        for (size_t i = 0; i < rhs_keys.size(); ++i) {
                            uint32_t rhs = rhs_keys[i];
                            uint32_t val = vals[i];

                            // Count for original entry
                            func_entries++;
                            Vlr_counts[val]++;
                            Rvl_counts[rhs]++;
                            Lvr_counts[lhs]++;

                            // Count for symmetric entry if needed
                            if (symmetric && lhs != rhs) {
                                func_entries++;
                                Vlr_counts[val]++;  // Same val, but (rhs, lhs)
                                                    // instead of (lhs, rhs)
                                Rvl_counts[lhs]++;  // Now indexed by lhs,
                                                    // stores (val, rhs)
                                Lvr_counts[rhs]++;  // Now indexed by rhs,
                                                    // stores (val, lhs)
                            }
                        }
                    }
                });

            // Create pointers from counts
            auto create_ptrs_from_counts =
                [](const std::vector<int>& counts) -> at::Tensor {
                at::Tensor ptrs =
                    at::zeros({static_cast<long>(counts.size() + 1)},
                              at::dtype(at::kInt));
                auto ptrs_acc = ptrs.accessor<int, 1>();
                for (size_t i = 0; i < counts.size(); ++i) {
                    ptrs_acc[i + 1] = ptrs_acc[i] + counts[i];
                }
                return ptrs;
            };

            at::Tensor Vlr_ptrs = create_ptrs_from_counts(Vlr_counts);
            at::Tensor Rvl_ptrs = create_ptrs_from_counts(Rvl_counts);
            at::Tensor Lvr_ptrs = create_ptrs_from_counts(Lvr_counts);

            int Vlr_nnz = Vlr_ptrs[Vlr_ptrs.size(0) - 1].item<int>();
            int Rvl_nnz = Rvl_ptrs[Rvl_ptrs.size(0) - 1].item<int>();
            int Lvr_nnz = Lvr_ptrs[Lvr_ptrs.size(0) - 1].item<int>();

            at::Tensor Vlr_args = at::zeros({Vlr_nnz, 2}, at::dtype(at::kInt));
            at::Tensor Rvl_args = at::zeros({Rvl_nnz, 2}, at::dtype(at::kInt));
            at::Tensor Lvr_args = at::zeros({Lvr_nnz, 2}, at::dtype(at::kInt));

            // Create hash table for LRv sparse function with optimal size
            // Use power-of-2 sizing like SparseBinaryFunction constructor
            int optimal_size = 1;
            while (optimal_size <= func_entries) {
                optimal_size <<= 1;
            }
            optimal_size <<= 1;  // Extra factor of 2 for good hash performance
            at::Tensor hash_table =
                at::zeros({optimal_size, 3}, at::dtype(at::kInt));

            // Pass 2: Fill data using visit_chunks
            std::vector<int> Vlr_pos(item_count + 1, 0);
            std::vector<int> Rvl_pos(item_count + 1, 0);
            std::vector<int> Lvr_pos(item_count + 1, 0);

            auto Vlr_ptrs_acc = Vlr_ptrs.accessor<int, 1>();
            auto Rvl_ptrs_acc = Rvl_ptrs.accessor<int, 1>();
            auto Lvr_ptrs_acc = Lvr_ptrs.accessor<int, 1>();
            auto Vlr_args_acc = Vlr_args.accessor<int, 2>();
            auto Rvl_args_acc = Rvl_args.accessor<int, 2>();
            auto Lvr_args_acc = Lvr_args.accessor<int, 2>();
            auto hash_table_acc = hash_table.accessor<int, 2>();

            // Helper function to insert into hash table using linear probing
            auto insert_into_hash_table = [&](int lhs, int rhs, int val) {
                int64_t hash_val = hash_pair(lhs, rhs);
                int h = static_cast<int>(std::abs(hash_val) % optimal_size);
                while (hash_table_acc[h][0] != 0) {
                    h = (h + 1) % optimal_size;
                }
                hash_table_acc[h][0] = lhs;
                hash_table_acc[h][1] = rhs;
                hash_table_acc[h][2] = val;
            };

            // Use visit_chunks again to fill the data structures
            visit_chunks(
                proto_func, [&](const atlas::protobuf::BinaryFunction& chunk) {
                    for (const auto& row : chunk.rows()) {
                        uint32_t lhs = row.lhs();
                        auto [rhs_keys, vals] = delta_decompress(row.rhs_val());

                        for (size_t i = 0; i < rhs_keys.size(); ++i) {
                            uint32_t rhs = rhs_keys[i];
                            uint32_t val = vals[i];

                            // Store in hash table for LRv
                            insert_into_hash_table(lhs, rhs, val);

                            // Vlr table: indexed by val, stores (lhs, rhs)
                            int idx = Vlr_ptrs_acc[val] + Vlr_pos[val];
                            Vlr_args_acc[idx][0] = lhs;
                            Vlr_args_acc[idx][1] = rhs;
                            Vlr_pos[val]++;

                            // Rvl table: indexed by rhs, stores (val, lhs)
                            idx = Rvl_ptrs_acc[rhs] + Rvl_pos[rhs];
                            Rvl_args_acc[idx][0] = val;
                            Rvl_args_acc[idx][1] = lhs;
                            Rvl_pos[rhs]++;

                            // Lvr table: indexed by lhs, stores (val, rhs)
                            idx = Lvr_ptrs_acc[lhs] + Lvr_pos[lhs];
                            Lvr_args_acc[idx][0] = val;
                            Lvr_args_acc[idx][1] = rhs;
                            Lvr_pos[lhs]++;

                            // Handle symmetric entries
                            if (symmetric && lhs != rhs) {
                                // Store symmetric entry in hash table
                                insert_into_hash_table(rhs, lhs, val);

                                // Vlr table: indexed by val, stores (rhs, lhs)
                                idx = Vlr_ptrs_acc[val] + Vlr_pos[val];
                                Vlr_args_acc[idx][0] = rhs;
                                Vlr_args_acc[idx][1] = lhs;
                                Vlr_pos[val]++;

                                // Rvl table: indexed by lhs (now the rhs),
                                // stores (val, rhs)
                                idx = Rvl_ptrs_acc[lhs] + Rvl_pos[lhs];
                                Rvl_args_acc[idx][0] = val;
                                Rvl_args_acc[idx][1] = rhs;
                                Rvl_pos[lhs]++;

                                // Lvr table: indexed by rhs (now the lhs),
                                // stores (val, lhs)
                                idx = Lvr_ptrs_acc[rhs] + Lvr_pos[rhs];
                                Lvr_args_acc[idx][0] = val;
                                Lvr_args_acc[idx][1] = lhs;
                                Lvr_pos[rhs]++;
                            }
                        }
                    }
                });

            // Add tensors with fully qualified names
            std::string func_prefix =
                (symmetric ? "symmetric_functions." : "binary_functions.") +
                func_name;

            keys.emplace_back(func_prefix + ".LRv");
            tensors.emplace_back(hash_table);

            keys.emplace_back(func_prefix + ".Vlr.ptrs");
            tensors.emplace_back(Vlr_ptrs);

            keys.emplace_back(func_prefix + ".Vlr.args");
            tensors.emplace_back(Vlr_args);

            keys.emplace_back(func_prefix + ".Rvl.ptrs");
            tensors.emplace_back(Rvl_ptrs);

            keys.emplace_back(func_prefix + ".Rvl.args");
            tensors.emplace_back(Rvl_args);

            keys.emplace_back(func_prefix + ".Lvr.ptrs");
            tensors.emplace_back(Lvr_ptrs);

            keys.emplace_back(func_prefix + ".Lvr.args");
            tensors.emplace_back(Lvr_args);
        };

    // Process binary functions
    for (const auto& proto_func : proto_structure.binary_functions()) {
        process_binary_function(proto_func, false);
    }

    // Process symmetric functions
    for (const auto& proto_func : proto_structure.symmetric_functions()) {
        process_binary_function(proto_func, true);
    }

    // Process relations if requested
    if (relations) {
        // TODO: Add unary and binary relations processing here if needed
        TORCH_CHECK(false, "Relations not implemented");
    }

    return std::make_tuple(std::move(keys), std::move(tensors));
}

template at::Tensor binary_function_reduce_product<false>(
    const at::Tensor& f_ptrs, const at::Tensor& f_args, const at::Tensor& lhs,
    const at::Tensor& rhs);

template at::Tensor binary_function_reduce_product<true>(
    const at::Tensor& f_ptrs, const at::Tensor& f_args, const at::Tensor& lhs,
    const at::Tensor& rhs);

}  // namespace torch
}  // namespace pomagma
