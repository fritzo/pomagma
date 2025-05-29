#pragma once

#include <ATen/ATen.h>
#include <torch/library.h>

namespace pomagma {
namespace torch {

// Function declarations for PyTorch operations
void iadd_binary_function(const at::Tensor& f_ptrs, const at::Tensor& f_args,
                          const at::Tensor& args, at::Tensor& out,
                          double weight);

// Add more function declarations here as needed

}  // namespace torch
}  // namespace pomagma