import functools
import logging
import os
import random
from typing import Mapping

import pytest
import torch
from immutables import Map

from .language import Language
from .structure import (
    BinaryFunction,
    BinaryFunctionSumProduct,
    Ob,
    SparseBinaryFunction,
    SparseTernaryRelation,
    Structure,
)

logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TEST_FILE = os.path.join(ROOT, "bootstrap", "atlas", "skrj", "region.normal.2047.pb")


@pytest.fixture(scope="session")
def structure() -> Structure:
    return Structure.load(TEST_FILE, relations=False)


@pytest.fixture(scope="session")
def language(structure: Structure) -> Language:
    # Use 1 + item_count because objects are 1-indexed (0 means undefined)
    nullary_functions = torch.zeros(1 + structure.item_count, dtype=torch.float32)
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


def make_dense_bin_fun(item_count: int) -> list[tuple[int, int, int]]:
    """Makes an integer multiplication table."""
    table: list[tuple[int, int, int]] = []
    for i in range(1, 1 + item_count):
        for j in range(1, 1 + item_count):
            k = i * j
            if k < item_count:
                table.append((i, j, k))
    return table


def make_sparse_binary_function(
    item_count: int, table: list[tuple[int, int, int]]
) -> SparseBinaryFunction:
    func = SparseBinaryFunction(item_count)
    for L, R, V in table:
        func[Ob(L), Ob(R)] = Ob(V)
    return func


def make_XYz_sparse(
    item_count: int, XYz_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    nnz = len(XYz_table)
    counts: list[int] = [0] * (1 + item_count)
    for X, Y, Z in XYz_table:
        counts[Z] += 1
    assert counts[0] == 0
    # 1 on the left for null, 1 on the right for end.
    ptrs = torch.empty(1 + item_count + 1, dtype=torch.int32)
    ptrs[0] = 0
    ptrs[1] = 0
    for i in range(1, 1 + item_count):
        ptrs[i + 1] = ptrs[i] + counts[i]
    assert ptrs[-1] == nnz
    pos = [0] * (1 + item_count)
    args = torch.empty((nnz, 2), dtype=torch.int32)
    for X, Y, Z in XYz_table:
        e = ptrs[Z] + pos[Z]
        args[e, 0] = X
        args[e, 1] = Y
        pos[Z] += 1
    assert pos == counts
    return ptrs, args


def make_LRv_sparse(
    item_count: int, LRv_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    return make_XYz_sparse(item_count, [(L, R, V) for L, R, V in LRv_table])


def make_VLr_sparse(
    item_count: int, LRv_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    return make_XYz_sparse(item_count, [(V, L, R) for L, R, V in LRv_table])


def make_VRl_sparse(
    item_count: int, LRv_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    return make_XYz_sparse(item_count, [(V, R, L) for L, R, V in LRv_table])


def make_binary_function(item_count: int) -> BinaryFunction:
    name = "MUL"
    table = make_dense_bin_fun(item_count)
    func = make_sparse_binary_function(item_count, table)
    LRv = SparseTernaryRelation(*make_LRv_sparse(item_count, table))
    VLr = SparseTernaryRelation(*make_VLr_sparse(item_count, table))
    VRl = SparseTernaryRelation(*make_VRl_sparse(item_count, table))
    return BinaryFunction(name, func, LRv, VLr, VRl)


@pytest.mark.parametrize("temperature", [True, False])
@pytest.mark.parametrize("item_count", [10, 100])
def test_binary_function(item_count: int, temperature: bool) -> None:
    table = make_dense_bin_fun(item_count)
    f_ptrs, f_args = make_LRv_sparse(item_count, table)

    lhs = torch.randn(1 + item_count, dtype=torch.float32)
    rhs = torch.randn(1 + item_count, dtype=torch.float32)

    if temperature:
        op = torch.ops.pomagma.binary_function_sum_product
    else:
        op = torch.ops.pomagma.binary_function_max_product

    out = op(f_ptrs, f_args, lhs, rhs)
    assert out.shape == (1 + item_count,)
    assert out.dtype == lhs.dtype
    assert out.device == lhs.device


@pytest.mark.parametrize("item_count", [5, 10])
def test_torch_binary_function_gradients(item_count: int) -> None:
    """Test that TorchBinaryFunction gradients are correctly implemented."""
    table = make_dense_bin_fun(item_count)

    # Create all three sparse representations
    LRv_ptrs, LRv_args = make_LRv_sparse(item_count, table)  # L,R -> V
    VLr_ptrs, VLr_args = make_VLr_sparse(item_count, table)  # V,L -> R
    VRl_ptrs, VRl_args = make_VRl_sparse(item_count, table)  # V,R -> L

    def torch_binary_function_wrapper(
        lhs: torch.Tensor, rhs: torch.Tensor
    ) -> torch.Tensor:
        return BinaryFunctionSumProduct.apply(
            LRv_ptrs, LRv_args, VLr_ptrs, VLr_args, VRl_ptrs, VRl_args, lhs, rhs
        )

    # Create test inputs that require gradients
    lhs = torch.randn(1 + item_count, dtype=torch.float, requires_grad=True)
    rhs = torch.randn(1 + item_count, dtype=torch.float, requires_grad=True)

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


def test_compute_probs(structure: Structure, language: Language) -> None:
    probs = language.compute_probs(structure)
    assert probs.shape == (structure.item_count + 1,)
    assert probs.dtype == torch.float32
    assert probs.device == torch.device("cpu")
    # Check probability mass (finite subset of infinite structure)
    total_prob = probs.sum().item()
    assert 0.5 <= total_prob <= 1.0


def test_log_prob(structure: Structure, language: Language) -> None:
    data = language
    probs = language.compute_probs(structure)
    log_prob = data.log_prob(language, probs)
    assert log_prob.shape == ()
    assert log_prob.dtype == torch.float32
    assert log_prob.device == torch.device("cpu")
    assert log_prob.item() < 0.0


# @pytest.mark.xfail(reason="Bug in compute_occurrences")
@pytest.mark.parametrize("item_count", [10])
def test_compute_rules_mul(item_count: int) -> None:
    # Build a structure, the multiplication table.
    mul = make_binary_function(item_count)
    primes: Mapping[str, Ob] = Map(
        {"ONE": Ob(1), "TWO": Ob(2), "THREE": Ob(3), "FIVE": Ob(5), "SEVEN": Ob(7)}
    )
    structure = Structure(
        name="MUL",
        item_count=item_count,
        nullary_functions=primes,
        binary_functions={"MUL": mul},
        symmetric_functions={},
        unary_relations={},
        binary_relations={},
    )

    # Build a language
    nullary_functions = torch.zeros(1 + item_count, dtype=torch.float32)
    nullary_functions[primes["ONE"]] = 1e-20
    nullary_functions[primes["TWO"]] = 0.1
    nullary_functions[primes["THREE"]] = 0.1
    nullary_functions[primes["FIVE"]] = 0.1
    nullary_functions[primes["SEVEN"]] = 0.1
    language = Language(
        nullary_functions=nullary_functions,
        binary_functions={"MUL": torch.tensor(0.5, dtype=torch.float32)},
        symmetric_functions={},
    )

    approx = functools.partial(pytest.approx, abs=1e-3, rel=1e-3)

    # Check a simple probe.
    weight = 12.34
    eight = torch.zeros(1 + item_count, dtype=torch.float32)
    eight[8] = weight
    rules = language.compute_rules(structure, eight)
    nullary = rules.nullary_functions
    assert nullary.shape == (1 + item_count,)
    assert nullary.dtype == torch.float32
    assert nullary.device == torch.device("cpu")
    assert nullary[2].item() == approx(3 * weight)
    assert nullary[3].item() == approx(0)
    assert nullary[4].item() == approx(0)
    assert nullary[5].item() == approx(0)
    assert nullary[6].item() == approx(0)
    assert nullary[7].item() == approx(0)
    assert nullary[8].item() == approx(0)
    assert nullary[9].item() == approx(0)
    assert nullary[10].item() == approx(0)

    # Check a simple probe.
    weight = 5.67
    six = torch.zeros(1 + item_count, dtype=torch.float32)
    six[6] = weight
    rules = language.compute_rules(structure, six)
    nullary = rules.nullary_functions
    assert nullary.shape == (1 + item_count,)
    assert nullary.dtype == torch.float32
    assert nullary.device == torch.device("cpu")
    assert nullary[2].item() == approx(weight)
    assert nullary[3].item() == approx(weight)
    assert nullary[4].item() == approx(0)
    assert nullary[5].item() == approx(0)
    assert nullary[6].item() == approx(0)
    assert nullary[7].item() == approx(0)
    assert nullary[8].item() == approx(0)
    assert nullary[9].item() == approx(0)
    assert nullary[10].item() == approx(0)


@pytest.mark.xfail(reason="Bug in compute_occurrences")
@pytest.mark.parametrize("item_count", [12])
def test_compute_occurrences_mul(item_count: int) -> None:
    # Build a structure, the multiplication table.
    mul = make_binary_function(item_count)
    primes: Mapping[str, Ob] = Map(
        {
            "ONE": Ob(1),
            "TWO": Ob(2),
            "THREE": Ob(3),
            "FIVE": Ob(5),
            "SEVEN": Ob(7),
            "ELEVEN": Ob(11),
        }
    )
    structure = Structure(
        name="MUL",
        item_count=item_count,
        nullary_functions=primes,
        binary_functions={"MUL": mul},
        symmetric_functions={},
        unary_relations={},
        binary_relations={},
    )

    # Build a language
    nullary_functions = torch.zeros(1 + item_count, dtype=torch.float32)
    nullary_functions[primes["ONE"]] = 1e-20
    nullary_functions[primes["TWO"]] = 0.1
    nullary_functions[primes["THREE"]] = 0.1
    nullary_functions[primes["FIVE"]] = 0.1
    nullary_functions[primes["SEVEN"]] = 0.1
    nullary_functions[primes["ELEVEN"]] = 0.1
    language = Language(
        nullary_functions=nullary_functions,
        binary_functions={"MUL": torch.tensor(0.5, dtype=torch.float32)},
        symmetric_functions={},
    )

    approx = functools.partial(pytest.approx, abs=1e-3, rel=1e-3)

    # Check a simple probe.
    weight = 12.34
    eight = torch.zeros(1 + item_count, dtype=torch.float32)
    eight[8] = weight
    occurrences = language.compute_occurrences(structure, eight)
    assert occurrences.shape == (1 + item_count,)
    assert occurrences.dtype == torch.float32
    assert occurrences.device == torch.device("cpu")
    # For 8 = 2*4, we should see occurrences of 2, 4, and 8 itself
    assert occurrences[2].item() == approx(3 * weight)  # 2 occurs in 2*2*2=8
    assert occurrences[3].item() == approx(0)
    assert occurrences[4].item() == approx(weight)  # 4 occurs in 2*4=8
    assert occurrences[5].item() == approx(0)
    assert occurrences[6].item() == approx(0)
    assert occurrences[7].item() == approx(0)
    assert occurrences[8].item() == approx(weight)  # 8 occurs as itself
    assert occurrences[9].item() == approx(0)
    assert occurrences[10].item() == approx(0)
    assert occurrences[11].item() == approx(0)
    assert occurrences[12].item() == approx(0)

    # Check another probe.
    weight = 5.67
    six = torch.zeros(1 + item_count, dtype=torch.float32)
    six[6] = weight
    occurrences = language.compute_occurrences(structure, six)
    assert occurrences.shape == (1 + item_count,)
    assert occurrences.dtype == torch.float32
    assert occurrences.device == torch.device("cpu")
    # For 6 = 2*3, we should see occurrences of 2, 3, and 6 itself
    assert occurrences[2].item() == approx(weight)  # 2 occurs in 2*3=6
    assert occurrences[3].item() == approx(weight)  # 3 occurs in 2*3=6
    assert occurrences[4].item() == approx(0)
    assert occurrences[5].item() == approx(0)
    assert occurrences[6].item() == approx(weight)  # 6 occurs as itself
    assert occurrences[7].item() == approx(0)
    assert occurrences[8].item() == approx(0)
    assert occurrences[9].item() == approx(0)
    assert occurrences[10].item() == approx(0)
    assert occurrences[11].item() == approx(0)
    assert occurrences[12].item() == approx(0)

    # Check another probe.
    weight = 8.9
    twelve = torch.zeros(1 + item_count, dtype=torch.float32)
    twelve[12] = weight
    occurrences = language.compute_occurrences(structure, twelve)
    assert occurrences.shape == (1 + item_count,)
    assert occurrences.dtype == torch.float32
    assert occurrences.device == torch.device("cpu")
    # For 12 = 2*2*3, we should see weight split between 4 and 6.
    assert occurrences[2].item() == approx(2 * weight)  # 2 occurs in 2*2*3=12
    assert occurrences[3].item() == approx(weight)  # 3 occurs in 2*2*3=12
    assert occurrences[4].item() == approx(1 / 3 * weight)  # 4 occurs in (2*2)*3=12
    assert occurrences[5].item() == approx(0)
    assert occurrences[6].item() == approx(2 / 3 * weight)  # 6 occurs in 2*(2*3)=12
    assert occurrences[7].item() == approx(0)
    assert occurrences[8].item() == approx(0)
    assert occurrences[9].item() == approx(0)
    assert occurrences[10].item() == approx(0)
    assert occurrences[11].item() == approx(0)
    assert occurrences[12].item() == approx(weight)  # 12 occurs as itself
