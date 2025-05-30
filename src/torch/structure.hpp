#pragma once

#include <ATen/ATen.h>
#include <torch/library.h>

namespace pomagma {
namespace torch {

// Function declarations for PyTorch operations

at::Tensor binary_function(const at::Tensor& f_ptrs, const at::Tensor& f_args,
                           const at::Tensor& lhs, const at::Tensor& rhs);

}  // namespace torch
}  // namespace pomagma