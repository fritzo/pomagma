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


def make_LRv_sparse(
    N: int, LRv_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    counts: list[int] = [0] * N
    for i, j, k in LRv_table:
        counts[k] += 1
    f_ptrs = torch.empty(N + 1, dtype=torch.int32)
    f_ptrs[0] = 0
    for i in range(N):
        f_ptrs[i + 1] = f_ptrs[i] + counts[i]

    nnz = sum(counts)
    pos = [0] * N
    f_args = torch.empty((nnz, 2), dtype=torch.int32)
    for i, j, k in LRv_table:
        e = f_ptrs[k] + pos[k]
        f_args[e, 0] = i
        f_args[e, 1] = j
        pos[k] += 1

    return f_ptrs, f_args


def make_LVr_sparse(
    N: int, LRv_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    """Create sparse representation mapping L -> (V,R) pairs."""
    counts: list[int] = [0] * N
    for L, R, V in LRv_table:
        counts[L] += 1

    ptrs = torch.empty(N + 1, dtype=torch.int32)
    ptrs[0] = 0
    for i in range(N):
        ptrs[i + 1] = ptrs[i] + counts[i]

    nnz = sum(counts)
    pos = [0] * N
    args = torch.empty((nnz, 2), dtype=torch.int32)
    for L, R, V in LRv_table:
        e = ptrs[L] + pos[L]
        args[e, 0] = V  # output index
        args[e, 1] = R  # other input index
        pos[L] += 1

    return ptrs, args


def make_RVl_sparse(
    N: int, LRv_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    """Create sparse representation mapping R -> (V,L) pairs."""
    counts: list[int] = [0] * N
    for L, R, V in LRv_table:
        counts[R] += 1

    ptrs = torch.empty(N + 1, dtype=torch.int32)
    ptrs[0] = 0
    for i in range(N):
        ptrs[i + 1] = ptrs[i] + counts[i]

    nnz = sum(counts)
    pos = [0] * N
    args = torch.empty((nnz, 2), dtype=torch.int32)
    for L, R, V in LRv_table:
        e = ptrs[R] + pos[R]
        args[e, 0] = V  # output index
        args[e, 1] = L  # other input index
        pos[R] += 1

    return ptrs, args


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
    LVr_ptrs, LVr_args = make_LVr_sparse(N, table)  # L -> V,R
    RVl_ptrs, RVl_args = make_RVl_sparse(N, table)  # R -> V,L

    def torch_binary_function_wrapper(
        lhs: torch.Tensor, rhs: torch.Tensor
    ) -> torch.Tensor:
        return TorchBinaryFunction.apply(
            LRv_ptrs, LRv_args, LVr_ptrs, LVr_args, RVl_ptrs, RVl_args, lhs, rhs
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
