// PyTorch extension for pomagma operations.
// For reference, see:
// https://docs.pytorch.org/tutorials/advanced/cpp_custom_ops.html

#include "structure.hpp"

#include <pomagma/io/protobuf.hpp>

namespace pomagma {
namespace torch {

void iadd_binary_function(const at::Tensor& f_ptrs, const at::Tensor& f_args,
                          const at::Tensor& args, at::Tensor& out,
                          double weight) {
    // Check shapes: f_ptrs [N+1], f_args [NNZ, 2], args [2, N], out [N]
    TORCH_CHECK(f_ptrs.dim() == 1);
    TORCH_CHECK(f_args.dim() == 2);
    TORCH_CHECK(args.dim() == 2);
    TORCH_CHECK(out.dim() == 1);
    const int64_t N = out.numel();
    const int64_t NNZ = f_args.size(0);
    TORCH_CHECK(f_ptrs.size(0) == N + 1);
    TORCH_CHECK(f_args.size(0) == NNZ);
    TORCH_CHECK(args.size(0) == 2);
    TORCH_CHECK(args.size(1) == N);
    TORCH_CHECK(out.size(0) == N);

    // Check dtypes
    TORCH_CHECK(f_ptrs.dtype() == at::kInt);
    TORCH_CHECK(f_args.dtype() == at::kInt);
    TORCH_CHECK(args.dtype() == at::kFloat);
    TORCH_CHECK(out.dtype() == at::kFloat);

    // Check all tensors are on CPU
    TORCH_CHECK(f_ptrs.device().type() == at::DeviceType::CPU);
    TORCH_CHECK(f_args.device().type() == at::DeviceType::CPU);
    TORCH_CHECK(args.device().type() == at::DeviceType::CPU);
    TORCH_CHECK(out.device().type() == at::DeviceType::CPU);

    // Check all tensors are contiguous
    TORCH_CHECK(f_ptrs.is_contiguous());
    TORCH_CHECK(f_args.is_contiguous());
    TORCH_CHECK(args.is_contiguous());
    TORCH_CHECK(out.is_contiguous());

    const int32_t* f_ptrs_data = f_ptrs.data_ptr<int32_t>();
    const int32_t* f_args_data = f_args.data_ptr<int32_t>();
    const float* lhs_data = args.data_ptr<float>();
    const float* rhs_data = lhs_data + N;
    float* out_data = out.data_ptr<float>();
    const float w = static_cast<float>(weight);

#pragma omp parallel for schedule(dynamic, 32)
    for (int64_t i = 0; i < N; i++) {
        float accum = 0;
        const int64_t begin = f_ptrs_data[i];
        const int64_t end = f_ptrs_data[i + 1];
        for (int64_t j = begin; j < end; j++) {
            const int64_t lhs = f_args_data[j * 2];
            const int64_t rhs = f_args_data[j * 2 + 1];
            accum += lhs_data[lhs] * rhs_data[rhs];
        }
        out_data[i] += w * accum;
    }
}

}  // namespace torch
}  // namespace pomagma
