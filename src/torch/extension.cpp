// PyTorch library registration for pomagma operators.
// This file contains the TORCH_LIBRARY registration separate from
// implementation.

#include "structure.hpp"

// Note: Use Tensor(a!) to indicate mutated tensors.
TORCH_LIBRARY(pomagma, m) {
    m.def(
        "binary_function(Tensor f_ptrs, Tensor f_args, Tensor lhs, "
        "Tensor rhs) -> Tensor");
}

TORCH_LIBRARY_IMPL(pomagma, CPU, m) {
    m.impl("binary_function", &pomagma::torch::binary_function);
}