#pragma once

#include <ATen/ATen.h>
#include <torch/library.h>

namespace pomagma {
namespace torch {

// Function declarations for PyTorch operations

template <bool temperature>
at::Tensor binary_function_reduce_product(const at::Tensor& f_ptrs,
                                          const at::Tensor& f_args,
                                          const at::Tensor& lhs,
                                          const at::Tensor& rhs);

extern template at::Tensor binary_function_reduce_product<false>(
    const at::Tensor& f_ptrs, const at::Tensor& f_args, const at::Tensor& lhs,
    const at::Tensor& rhs);
extern template at::Tensor binary_function_reduce_product<true>(
    const at::Tensor& f_ptrs, const at::Tensor& f_args, const at::Tensor& lhs,
    const at::Tensor& rhs);

at::Tensor binary_function_distribute_product(const at::Tensor& f_ptrs,
                                              const at::Tensor& f_args,
                                              const at::Tensor& parent_counts,
                                              const at::Tensor& probs,
                                              double weight);

// Hash function for SparseBinaryFunction
int64_t hash_pair(int64_t lhs, int64_t rhs);

// Structure loading function (stub for testing) - returns parallel arrays of
// keys and tensors
std::tuple<std::vector<std::string>, std::vector<at::Tensor>>
load_structure_cpp(const std::string& filename, bool relations);

}  // namespace torch
}  // namespace pomagma