import pytest
import torch

from .structure import TorchBinaryFunction


def make_dense_bin_fun(N: int) -> list[tuple[int, int, int]]:
    table: list[tuple[int, int, int]] = []
    for i in range(N):
        for j in range(N):
            k = i * j
            if k < N:
                table.append((i, j, k))
    return table


def make_XYz_sparse(
    N: int, XYz_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    counts: list[int] = [0] * N
    for X, Y, Z in XYz_table:
        counts[Z] += 1
    ptrs = torch.empty(N + 1, dtype=torch.int32)
    ptrs[0] = 0
    for i in range(N):
        ptrs[i + 1] = ptrs[i] + counts[i]
    nnz = sum(counts)
    pos = [0] * N
    args = torch.empty((nnz, 2), dtype=torch.int32)
    for X, Y, Z in XYz_table:
        e = ptrs[Z] + pos[Z]
        args[e, 0] = X
        args[e, 1] = Y
        pos[Z] += 1
    return ptrs, args


def make_LRv_sparse(
    N: int, LRv_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    return make_XYz_sparse(N, [(L, R, V) for L, R, V in LRv_table])


def make_VLr_sparse(
    N: int, LRv_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    return make_XYz_sparse(N, [(V, L, R) for L, R, V in LRv_table])


def make_VRl_sparse(
    N: int, LRv_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    return make_XYz_sparse(N, [(V, R, L) for L, R, V in LRv_table])


@pytest.mark.parametrize("N", [10, 100])
def test_binary_function(N: int) -> None:
    table = make_dense_bin_fun(N)
    f_ptrs, f_args = make_LRv_sparse(N, table)

    lhs = torch.randn(N, dtype=torch.float32)
    rhs = torch.randn(N, dtype=torch.float32)

    out = torch.ops.pomagma.binary_function(f_ptrs, f_args, lhs, rhs)
    assert out.shape == (N,)
    assert out.dtype == lhs.dtype
    assert out.device == lhs.device


@pytest.mark.parametrize("N", [5, 10])
def test_torch_binary_function_gradients(N: int) -> None:
    """Test that TorchBinaryFunction gradients are correctly implemented."""
    table = make_dense_bin_fun(N)

    # Create all three sparse representations
    LRv_ptrs, LRv_args = make_LRv_sparse(N, table)  # L,R -> V
    VLr_ptrs, VLr_args = make_VLr_sparse(N, table)  # V,L -> R
    VRl_ptrs, VRl_args = make_VRl_sparse(N, table)  # V,R -> L

    def torch_binary_function_wrapper(
        lhs: torch.Tensor, rhs: torch.Tensor
    ) -> torch.Tensor:
        return TorchBinaryFunction.apply(
            LRv_ptrs, LRv_args, VLr_ptrs, VLr_args, VRl_ptrs, VRl_args, lhs, rhs
        )

    # Create test inputs that require gradients
    lhs = torch.randn(N, dtype=torch.float, requires_grad=True)
    rhs = torch.randn(N, dtype=torch.float, requires_grad=True)

    # Test gradients using PyTorch's gradient checker
    assert torch.autograd.gradcheck(
        torch_binary_function_wrapper,
        (lhs, rhs),
        eps=1e-3,
        atol=1e-2,
        check_undefined_grad=False,  # We return None for non-differentiable args
    ), "Gradient check failed for TorchBinaryFunction"


# TODO test TorchBinaryFunction
