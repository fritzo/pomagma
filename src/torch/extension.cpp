// PyTorch library registration for pomagma operators.
// This file contains the TORCH_LIBRARY registration separate from
// implementation.

#include "structure.hpp"

// Note: Use Tensor(a!) to indicate mutated tensors.
TORCH_LIBRARY(pomagma, m) {
    m.def(
        "binary_function_sum_product(Tensor f_ptrs, Tensor f_args, Tensor lhs, "
        "Tensor rhs) -> Tensor");
    m.def(
        "binary_function_max_product(Tensor f_ptrs, Tensor f_args, Tensor lhs, "
        "Tensor rhs) -> Tensor");
    m.def(
        "binary_function_distribute_product(Tensor f_ptrs, Tensor f_args, "
        "Tensor parent_counts, Tensor probs, float weight) -> Tensor");
}

TORCH_LIBRARY_IMPL(pomagma, CPU, m) {
    m.impl("binary_function_sum_product",
           &pomagma::torch::binary_function_reduce_product<true>);
    m.impl("binary_function_max_product",
           &pomagma::torch::binary_function_reduce_product<false>);
    m.impl("binary_function_distribute_product",
           &pomagma::torch::binary_function_distribute_product);
}