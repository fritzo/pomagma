import pytest
import torch


def make_dense_bin_fun(N: int) -> list[tuple[int, int, int]]:
    table: list[tuple[int, int, int]] = []
    for i in range(N):
        for j in range(N):
            k = i * j
            if k < N:
                table.append((i, j, k))
    return table


def make_sparse_bin_fun(
    N: int, table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    counts: list[int] = [0] * N
    for i, j, k in table:
        counts[k] += 1
    f_ptrs = torch.empty(N + 1, dtype=torch.int32)
    f_ptrs[0] = 0
    for i in range(N):
        f_ptrs[i + 1] = f_ptrs[i] + counts[i]

    nnz = sum(counts)
    pos = [0] * N
    f_args = torch.empty((nnz, 2), dtype=torch.int32)
    for i, j, k in table:
        e = f_ptrs[k] + pos[k]
        f_args[e, 0] = i
        f_args[e, 1] = j
        pos[k] += 1

    return f_ptrs, f_args


@pytest.mark.parametrize("N", [10, 100])
def test_binary_function_fwd(N: int) -> None:
    table = make_dense_bin_fun(N)
    f_ptrs, f_args = make_sparse_bin_fun(N, table)

    lhs = torch.randn(N, dtype=torch.float32)
    rhs = torch.randn(N, dtype=torch.float32)

    out = torch.ops.pomagma.binary_function_fwd(f_ptrs, f_args, lhs, rhs)
    assert out.shape == (N,)
    assert out.dtype == lhs.dtype
    assert out.device == lhs.device
