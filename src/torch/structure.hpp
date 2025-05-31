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

}  // namespace torch
}  // namespace pomagma