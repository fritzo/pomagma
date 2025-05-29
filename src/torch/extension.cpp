// PyTorch library registration for pomagma operators.
// This file contains the TORCH_LIBRARY registration separate from
// implementation.

#include "structure.hpp"

TORCH_LIBRARY(pomagma, m) {
    // Note: Using Tensor(a!) to indicate that 'out' is mutated
    m.def(
        "iadd_binary_function(Tensor f_ptrs, Tensor f_args, Tensor args, "
        "Tensor(a!) out, float weight) -> ()");
}

TORCH_LIBRARY_IMPL(pomagma, CPU, m) {
    m.impl("iadd_binary_function", &pomagma::torch::iadd_binary_function);
}