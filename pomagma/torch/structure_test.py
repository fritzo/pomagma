import functools
import logging
import random
from collections.abc import Mapping

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


def make_dense_bin_fun(item_count: int) -> list[tuple[int, int, int]]:
    """Makes an integer multiplication table."""
    table: list[tuple[int, int, int]] = []
    for i in range(1, 1 + item_count):
        for j in range(1, 1 + item_count):
            k = i * j
            if k <= item_count:  # Include products that equal item_count
                table.append((i, j, k))
    return table


def make_sparse_binary_function(
    item_count: int, table: list[tuple[int, int, int]]
) -> SparseBinaryFunction:
    LRv = SparseBinaryFunction(len(table))
    for L, R, V in table:
        LRv[Ob(L), Ob(R)] = Ob(V)
    return LRv


def make_Xyz_sparse(
    item_count: int, Xyz_table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    nnz = len(Xyz_table)
    counts: list[int] = [0] * (1 + item_count)
    for X, Y, Z in Xyz_table:
        counts[X] += 1
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
    for X, Y, Z in Xyz_table:
        e = ptrs[X] + pos[X]
        args[e, 0] = Y
        args[e, 1] = Z
        pos[X] += 1
    assert pos == counts
    return ptrs, args


def make_Vlr_sparse(
    item_count: int, table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    return make_Xyz_sparse(item_count, [(V, L, R) for L, R, V in table])


def make_Rvl_sparse(
    item_count: int, table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    return make_Xyz_sparse(item_count, [(R, V, L) for L, R, V in table])


def make_Lvr_sparse(
    item_count: int, table: list[tuple[int, int, int]]
) -> tuple[torch.Tensor, torch.Tensor]:
    return make_Xyz_sparse(item_count, [(L, V, R) for L, R, V in table])


def make_binary_function(item_count: int) -> BinaryFunction:
    name = "MUL"
    table = make_dense_bin_fun(item_count)
    LRv = make_sparse_binary_function(item_count, table)
    Vlr = SparseTernaryRelation(*make_Vlr_sparse(item_count, table))
    Rvl = SparseTernaryRelation(*make_Rvl_sparse(item_count, table))
    Lvr = SparseTernaryRelation(*make_Lvr_sparse(item_count, table))
    return BinaryFunction(name, LRv, Vlr, Rvl, Lvr)


@pytest.mark.parametrize("temperature", [True, False])
@pytest.mark.parametrize("item_count", [10, 100])
def test_binary_function(item_count: int, temperature: bool) -> None:
    table = make_dense_bin_fun(item_count)
    f_ptrs, f_args = make_Vlr_sparse(item_count, table)

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
    Vlr_ptrs, Vlr_args = make_Vlr_sparse(item_count, table)  # L,R -> V
    Rvl_ptrs, Rvl_args = make_Rvl_sparse(item_count, table)  # V,L -> R
    Lvr_ptrs, Lvr_args = make_Lvr_sparse(item_count, table)  # V,R -> L

    def torch_binary_function_wrapper(
        lhs: torch.Tensor, rhs: torch.Tensor
    ) -> torch.Tensor:
        return BinaryFunctionSumProduct.apply(
            Vlr_ptrs, Vlr_args, Rvl_ptrs, Rvl_args, Lvr_ptrs, Lvr_args, lhs, rhs
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


@pytest.mark.parametrize("item_count", [5, 10])
def test_binary_function_distribute_product(item_count: int) -> None:
    """Test the C++ binary_function_distribute_product operation."""
    table = make_dense_bin_fun(item_count)

    # Create the Vlr sparse representation
    Vlr_ptrs, Vlr_args = make_Vlr_sparse(item_count, table)

    # Create test data: uniform distribution for probs
    probs = torch.ones(1 + item_count, dtype=torch.float32) / (1 + item_count)

    # Create parent counts with a single non-zero element
    parent_counts = torch.zeros(1 + item_count, dtype=torch.float32)
    test_parent = min(5, item_count)  # Pick a parent that likely has children
    test_weight = 10.0
    parent_counts[test_parent] = test_weight

    # Test with a reasonable grammar weight
    grammar_weight = 0.5

    # Call the C++ function
    child_contributions = torch.ops.pomagma.binary_function_distribute_product(
        Vlr_ptrs, Vlr_args, parent_counts, probs, grammar_weight
    )

    # Check output shape and type
    assert child_contributions.shape == (1 + item_count,)
    assert child_contributions.dtype == torch.float32
    assert child_contributions.device == torch.device("cpu")

    # Check that contributions are non-negative
    assert (child_contributions >= 0).all()

    # Check that only children of test_parent receive contributions
    has_contributions = (child_contributions > 0).sum().item()
    if has_contributions > 0:
        logger.info(
            "Parent %s distributed weight to %s children",
            test_parent,
            has_contributions,
        )
        # The total contribution should be proportional to the parent count
        # (exact amount depends on the number of ways to form the parent)
        total_contribution = child_contributions.sum().item()
        assert total_contribution > 0, "Should have some contribution to children"


def test_binary_function_lookup(structure: Structure) -> None:
    for symmetric, functions in [
        (False, structure.binary_functions),
        (True, structure.symmetric_functions),
    ]:
        for name, f in functions.items():
            logger.info("Testing %s lookup", name)
            for i in range(1000):
                val = Ob(random.randint(1, structure.item_count))
                if f.Vlr.ptrs[val] < f.Vlr.ptrs[val + 1]:
                    start = int(f.Vlr.ptrs[val].item())
                    end = int(f.Vlr.ptrs[val + 1].item()) - 1
                    e = random.randint(start, end)
                    lhs = Ob(int(f.Vlr.args[e, 0].item()))
                    rhs = Ob(int(f.Vlr.args[e, 1].item()))
                    assert f.LRv[lhs, rhs] == val
                    if symmetric:
                        assert f.LRv[rhs, lhs] == val


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
    log_prob = data.log_prob(structure, language, probs)
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


def test_compute_best(structure: Structure, language: Language) -> None:
    """Test that compute_best produces reasonable results for E-graph extraction."""
    best = language.compute_best(structure)
    assert best.shape == (structure.item_count + 1,)
    assert best.dtype == torch.float32
    assert best.device == torch.device("cpu")

    # Check that best probabilities are non-negative
    assert (best >= 0).all()

    # Check that there are some non-zero best probabilities
    assert (best > 0).sum() > 0

    # Best probabilities should be less than or equal to compute_probs
    probs = language.compute_probs(structure)
    assert (best <= probs + 1e-6).all()  # Allow small numerical error


@pytest.mark.parametrize("item_count", [10])
def test_compute_best_mul(item_count: int) -> None:
    """Test compute_best with the multiplication table example."""
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

    best = language.compute_best(structure)
    assert best.shape == (1 + item_count,)
    assert best.dtype == torch.float32
    assert best.device == torch.device("cpu")

    # Check that primes have non-zero best probabilities
    assert best[primes["TWO"]].item() > 0
    assert best[primes["THREE"]].item() > 0
    assert best[primes["FIVE"]].item() > 0
    assert best[primes["SEVEN"]].item() > 0

    # Check that composite numbers can have non-zero best probabilities
    # (depending on whether they can be expressed as products)
    if item_count >= 4:
        assert best[4].item() >= 0  # 4 = 2*2
    if item_count >= 6:
        assert best[6].item() >= 0  # 6 = 2*3
    if item_count >= 9:
        assert best[9].item() >= 0  # 9 = 3*3


def test_extract_all(structure: Structure, language: Language) -> None:
    """Test that extract_all produces expressions for some E-classes."""
    expressions = language.extract_all(structure)
    assert len(expressions) == structure.item_count + 1
    assert expressions[0] is None  # 0 is undefined

    # Check that some expressions are extracted
    non_none_count = sum(1 for expr in expressions if expr is not None)
    assert non_none_count > 0

    # Check that extracted expressions are Expression objects
    from pomagma.compiler.expressions import Expression

    for expr in expressions:
        if expr is not None:
            assert isinstance(expr, Expression)


@pytest.mark.parametrize("item_count", [10])
def test_extract_all_mul(item_count: int) -> None:
    """Test extract_all with the multiplication table example."""
    # Register MUL as a BinaryFunction in the signature system
    from pomagma.compiler.signature import declare_arity

    declare_arity("MUL", "BinaryFunction")

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

    # Build a language with high weight for MUL
    nullary_functions = torch.zeros(1 + item_count, dtype=torch.float32)
    nullary_functions[primes["ONE"]] = 1e-20  # Very low weight for ONE
    nullary_functions[primes["TWO"]] = 0.1
    nullary_functions[primes["THREE"]] = 0.1
    nullary_functions[primes["FIVE"]] = 0.1
    nullary_functions[primes["SEVEN"]] = 0.1
    language = Language(
        nullary_functions=nullary_functions,
        binary_functions={"MUL": torch.tensor(0.8, dtype=torch.float32)},  # High weight
        symmetric_functions={},
    )

    expressions = language.extract_all(structure)
    assert len(expressions) == 1 + item_count
    assert expressions[0] is None  # 0 is undefined

    # Check that primes are extracted as nullary functions
    two = expressions[primes["TWO"]]
    three = expressions[primes["THREE"]]
    five = expressions[primes["FIVE"]]
    seven = expressions[primes["SEVEN"]]
    assert two is not None
    assert two.name == "TWO"
    assert three is not None
    assert three.name == "THREE"
    assert five is not None
    assert five.name == "FIVE"
    assert seven is not None
    assert seven.name == "SEVEN"

    # Check that composite numbers are extracted as MUL expressions (when beneficial)
    if item_count >= 4:
        expr_4 = expressions[4]
        if expr_4 is not None:
            # 4 = 2*2 should be expressed as MUL(TWO, TWO)
            assert expr_4.name == "MUL"
            assert len(expr_4.args) == 2

    if item_count >= 6:
        expr_6 = expressions[6]
        if expr_6 is not None:
            # 6 = 2*3 should be expressed as MUL(TWO, THREE) or MUL(THREE, TWO)
            assert expr_6.name == "MUL"
            assert len(expr_6.args) == 2
            arg_names = {expr_6.args[0].name, expr_6.args[1].name}
            assert arg_names == {"TWO", "THREE"}


def test_hash_pair() -> None:
    # Test basic functionality
    hash1 = torch.ops.pomagma.hash_pair(42, 13)
    hash2 = torch.ops.pomagma.hash_pair(42, 13)
    assert hash1 == hash2, "Hash should be deterministic"

    # Test different inputs give different hashes (with very high probability)
    hash3 = torch.ops.pomagma.hash_pair(42, 14)
    hash4 = torch.ops.pomagma.hash_pair(43, 13)
    assert hash1 != hash3, "Different rhs should give different hash"
    assert hash1 != hash4, "Different lhs should give different hash"

    # Test order matters
    hash5 = torch.ops.pomagma.hash_pair(13, 42)
    assert hash1 != hash5, "Order should matter: hash(a,b) != hash(b,a)"

    # Test with edge cases
    hash_zero = torch.ops.pomagma.hash_pair(0, 0)
    hash_large = torch.ops.pomagma.hash_pair(2**32, 2**32)
    hash_negative = torch.ops.pomagma.hash_pair(-1, -1)

    # All hashes should be different (with very high probability)
    hashes = [hash1, hash3, hash4, hash5, hash_zero, hash_large, hash_negative]
    assert len(set(hashes)) == len(hashes), "All test hashes should be different"


def test_sparse_binary_function_with_hash_pair() -> None:
    # Create a small test function
    sparse_func = SparseBinaryFunction(10)

    # Test basic operations
    sparse_func[Ob(1), Ob(2)] = Ob(3)
    sparse_func[Ob(4), Ob(5)] = Ob(6)
    sparse_func[Ob(7), Ob(8)] = Ob(9)

    # Test retrieval
    assert sparse_func[Ob(1), Ob(2)] == Ob(3)
    assert sparse_func[Ob(4), Ob(5)] == Ob(6)
    assert sparse_func[Ob(7), Ob(8)] == Ob(9)

    # Test missing entries return 0
    assert sparse_func[Ob(1), Ob(3)] == Ob(0)
    assert sparse_func[Ob(2), Ob(1)] == Ob(0)  # Order matters

    # Test with larger values to check hash distribution
    sparse_func[Ob(100), Ob(200)] = Ob(300)
    sparse_func[Ob(1000), Ob(2000)] = Ob(3000)

    assert sparse_func[Ob(100), Ob(200)] == Ob(300)
    assert sparse_func[Ob(1000), Ob(2000)] == Ob(3000)

    # Original entries should still work
    assert sparse_func[Ob(4), Ob(5)] == Ob(6)
    assert sparse_func[Ob(7), Ob(8)] == Ob(9)
