import logging
import os
import random

import pytest
import torch

from .language import Language
from .structure import BinaryFunctionSumProduct, Ob, Structure

logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TEST_FILE = os.path.join(ROOT, "bootstrap", "atlas", "skrj", "region.normal.2047.pb")


@pytest.fixture(scope="session")
def structure() -> Structure:
    return Structure.load(TEST_FILE, relations=False)


def make_dense_bin_fun(N: int) -> list[tuple[int, int, int]]:
    table: list[tuple[int, int, int]] = []
    for i in range(N):
        for j in range(N):
            k = i * j
            if k < N:
                table.append((i, j, k))
    return table


@pytest.fixture(scope="session")
def language(structure: Structure) -> Language:
    # Use item_count + 1 because objects are 1-indexed (0 means undefined)
    nullary_functions = torch.zeros(structure.item_count + 1, dtype=torch.float32)
    nullary_functions[structure.nullary_functions["S"]] = 0.1
    nullary_functions[structure.nullary_functions["K"]] = 0.1
    nullary_functions[structure.nullary_functions["J"]] = 0.1
    nullary_functions[structure.nullary_functions["R"]] = 0.1
    binary_functions = {
        "APP": torch.tensor(0.2, dtype=torch.float32),
        "COMP": torch.tensor(0.2, dtype=torch.float32),
    }
    symmetric_functions = {
        "JOIN": torch.tensor(0.2, dtype=torch.float32),
    }
    language = Language(
        nullary_functions=nullary_functions,
        binary_functions=binary_functions,
        symmetric_functions=symmetric_functions,
    )
    return language


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


@pytest.mark.parametrize("temperature", [True, False])
@pytest.mark.parametrize("N", [10, 100])
def test_binary_function(N: int, temperature: bool) -> None:
    table = make_dense_bin_fun(N)
    f_ptrs, f_args = make_LRv_sparse(N, table)

    lhs = torch.randn(N, dtype=torch.float32)
    rhs = torch.randn(N, dtype=torch.float32)

    if temperature:
        op = torch.ops.pomagma.binary_function_sum_product
    else:
        op = torch.ops.pomagma.binary_function_max_product

    out = op(f_ptrs, f_args, lhs, rhs)
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
        return BinaryFunctionSumProduct.apply(
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


def test_binary_function_lookup(structure: Structure) -> None:
    for symmetric, functions in [
        (False, structure.binary_functions),
        (True, structure.symmetric_functions),
    ]:
        for name, f in functions.items():
            logger.info(f"Testing {name} lookup")
            for i in range(1000):
                val = Ob(random.randint(1, structure.item_count))
                if f.LRv.ptrs[val] < f.LRv.ptrs[val + 1]:
                    start = int(f.LRv.ptrs[val].item())
                    end = int(f.LRv.ptrs[val + 1].item()) - 1
                    e = random.randint(start, end)
                    lhs = Ob(int(f.LRv.args[e, 0].item()))
                    rhs = Ob(int(f.LRv.args[e, 1].item()))
                    assert f.func[lhs, rhs] == val
                    if symmetric:
                        assert f.func[rhs, lhs] == val


def test_propagate_probs(structure: Structure, language: Language) -> None:
    probs = language.propagate_probs(structure)
    assert probs.shape == (structure.item_count + 1,)
    assert probs.dtype == torch.float32
    assert probs.device == torch.device("cpu")
    # Check probability mass (finite subset of infinite structure)
    total_prob = probs.sum().item()
    assert 0.5 <= total_prob <= 1.0


def test_log_prob(structure: Structure, language: Language) -> None:
    log_prob = language.log_prob(language)
    assert log_prob.shape == ()
    assert log_prob.dtype == torch.float32
    assert log_prob.device == torch.device("cpu")
    assert log_prob.item() < 0.0
