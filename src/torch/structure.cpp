// PyTorch extension for pomagma operations.
// For reference, see:
// https://docs.pytorch.org/tutorials/advanced/cpp_custom_ops.html

#include "structure.hpp"

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

template at::Tensor binary_function_reduce_product<false>(
    const at::Tensor& f_ptrs, const at::Tensor& f_args, const at::Tensor& lhs,
    const at::Tensor& rhs);

template at::Tensor binary_function_reduce_product<true>(
    const at::Tensor& f_ptrs, const at::Tensor& f_args, const at::Tensor& lhs,
    const at::Tensor& rhs);

}  // namespace torch
}  // namespace pomagma
