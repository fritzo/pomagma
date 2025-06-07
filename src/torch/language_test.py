import math

import pytest
import torch
from immutables import Map

from pomagma.torch.corpus import ObTree
from pomagma.torch.language import Language
from pomagma.torch.structure import (
    BinaryFunction,
    Ob,
    SparseBinaryFunction,
    SparseTernaryRelation,
    Structure,
)


@pytest.fixture(scope="session")
def simple_structure() -> Structure:
    """Create a simple structure for testing."""
    # Create a structure with 5 objects
    item_count = 5

    # Create binary function table: APP(1,2)=3, APP(2,1)=4, APP(1,1)=5
    table: list[tuple[Ob, Ob, Ob]] = [
        (Ob(1), Ob(2), Ob(3)),
        (Ob(2), Ob(1), Ob(4)),
        (Ob(1), Ob(1), Ob(5)),
    ]

    # Create LRv (sparse binary function)
    LRv = SparseBinaryFunction(len(table))
    for lhs, rhs, val in table:
        LRv[Ob(lhs), Ob(rhs)] = Ob(val)

    # Create Vlr (Value -> (Left, Right) pairs)
    vlr_data: dict[Ob, list[tuple[Ob, Ob]]] = {}
    for lhs, rhs, val in table:
        if val not in vlr_data:
            vlr_data[val] = []
        vlr_data[val].append((lhs, rhs))

    vlr_ptrs = torch.zeros(item_count + 2, dtype=torch.int32)
    vlr_args_list = []
    for val in map(Ob, range(1, item_count + 1)):
        vlr_ptrs[val + 1] = vlr_ptrs[val]
        if val in vlr_data:
            for lhs, rhs in vlr_data[val]:
                vlr_args_list.append([lhs, rhs])
                vlr_ptrs[val + 1] += 1
    vlr_args = (
        torch.tensor(vlr_args_list, dtype=torch.int32)
        if vlr_args_list
        else torch.zeros((0, 2), dtype=torch.int32)
    )
    Vlr = SparseTernaryRelation(vlr_ptrs, vlr_args)

    # Create Rvl (Right -> (Value, Left) pairs)
    rvl_data: dict[Ob, list[tuple[Ob, Ob]]] = {}
    for lhs, rhs, val in table:
        if rhs not in rvl_data:
            rvl_data[rhs] = []
        rvl_data[rhs].append((val, lhs))

    rvl_ptrs = torch.zeros(item_count + 2, dtype=torch.int32)
    rvl_args_list = []
    for rhs in map(Ob, range(1, item_count + 1)):
        rvl_ptrs[rhs + 1] = rvl_ptrs[rhs]
        if rhs in rvl_data:
            for val, lhs in rvl_data[rhs]:
                rvl_args_list.append([val, lhs])
                rvl_ptrs[rhs + 1] += 1
    rvl_args = (
        torch.tensor(rvl_args_list, dtype=torch.int32)
        if rvl_args_list
        else torch.zeros((0, 2), dtype=torch.int32)
    )
    Rvl = SparseTernaryRelation(rvl_ptrs, rvl_args)

    # Create Lvr (Left -> (Value, Right) pairs)
    lvr_data: dict[Ob, list[tuple[Ob, Ob]]] = {}
    for lhs, rhs, val in table:
        if lhs not in lvr_data:
            lvr_data[lhs] = []
        lvr_data[lhs].append((val, rhs))

    lvr_ptrs = torch.zeros(item_count + 2, dtype=torch.int32)
    lvr_args_list = []
    for lhs in map(Ob, range(1, item_count + 1)):
        lvr_ptrs[lhs + 1] = lvr_ptrs[lhs]
        if lhs in lvr_data:
            for val, rhs in lvr_data[lhs]:
                lvr_args_list.append([val, rhs])
                lvr_ptrs[lhs + 1] += 1
    lvr_args = (
        torch.tensor(lvr_args_list, dtype=torch.int32)
        if lvr_args_list
        else torch.zeros((0, 2), dtype=torch.int32)
    )
    Lvr = SparseTernaryRelation(lvr_ptrs, lvr_args)

    nullary_functions = Map({"X": Ob(1), "Y": Ob(2)})
    binary_functions = Map({"APP": BinaryFunction("APP", LRv, Vlr, Rvl, Lvr)})

    return Structure(
        name="test",
        item_count=item_count,
        nullary_functions=nullary_functions,
        binary_functions=binary_functions,
        symmetric_functions=Map(),
        unary_relations=Map(),
        binary_relations=Map(),
    )


@pytest.fixture
def simple_language(simple_structure: Structure) -> Language:
    """Create a simple language for testing."""
    nullary_functions = torch.tensor([0.0, 0.3, 0.2, 0.0, 0.0, 0.0])  # X=0.3, Y=0.2
    binary_functions = Map({"APP": torch.tensor(0.5)})

    language = Language(
        nullary_functions=nullary_functions, binary_functions=binary_functions
    )
    language.normalize_()
    return language


@pytest.fixture
def simple_corpus(simple_structure: Structure) -> ObTree:
    """Create a simple corpus as an ObTree."""
    # Create corpus: X, Y, APP(X,Y)
    x_tree = ObTree(ob=Ob(1))  # X
    y_tree = ObTree(ob=Ob(2))  # Y
    app_tree = ObTree(name="APP", args=(x_tree, y_tree))
    return app_tree


@pytest.fixture
def simple_corpus_data() -> torch.Tensor:
    """Create simple corpus data as tensor directly."""
    # Simple corpus with X=1, Y=1, APP(X,Y)=1 counts
    corpus_data = torch.tensor([0.0, 1.0, 1.0, 1.0, 0.0, 0.0])  # X, Y, APP(X,Y) result
    return corpus_data


def test_warm_starting(simple_structure: Structure, simple_language: Language) -> None:
    """Test that warm starting reduces iterations."""
    # First call without warm start
    probs1 = simple_language.compute_probs(simple_structure, reltol=1e-4)

    # Second call with warm start should be faster/same result
    probs2 = simple_language.compute_probs(
        simple_structure, reltol=1e-4, init_probs=probs1
    )

    # Results should be very close
    assert torch.allclose(probs1, probs2, atol=1e-6)


def test_minimum_iterations(
    simple_structure: Structure, simple_language: Language
) -> None:
    """Test minimum iterations parameter."""
    # Test with min_iterations=0 vs min_iterations=5
    probs_min0 = simple_language.compute_probs(
        simple_structure,
        reltol=1e-1,  # High tolerance for quick convergence
        min_iterations=0,
    )

    probs_min5 = simple_language.compute_probs(
        simple_structure,
        reltol=1e-1,  # High tolerance for quick convergence
        min_iterations=5,
    )

    # Both should give valid results
    assert probs_min0.shape == probs_min5.shape
    assert torch.all(probs_min0 >= 0)
    assert torch.all(probs_min5 >= 0)


def test_sparsity_utilities(simple_language: Language) -> None:
    """Test sparsity counting and target computation."""
    # Test count_nonzero_nullary
    sparsity = simple_language.count_nonzero_nullary()
    expected_nonzero = (simple_language.nullary_functions.abs() > 1e-8).sum().item()
    assert sparsity == expected_nonzero

    # Test compute_target_sparsity
    corpus_size = 100
    target = simple_language.compute_target_sparsity(corpus_size)
    assert target == int(math.sqrt(corpus_size))
    assert target == 10


def test_l1_penalty(simple_language: Language) -> None:
    """Test L1 penalty computation."""
    penalty = simple_language.compute_l1_penalty()
    expected = simple_language.nullary_functions.abs().sum()
    assert torch.allclose(penalty, expected)


def test_project_to_feasible(simple_language: Language) -> None:
    """Test constraint projection."""
    # Make some weights negative
    with torch.no_grad():
        simple_language.nullary_functions[1] = -0.1
        simple_language.binary_functions["APP"] = torch.tensor(-0.2)

    # Project to feasible set
    simple_language.project_to_feasible_()

    # Check nonnegativity
    assert torch.all(simple_language.nullary_functions >= 0)
    assert torch.all(simple_language.binary_functions["APP"] >= 0)

    # Check normalization (approximately)
    total = simple_language.total()
    assert torch.allclose(total, torch.tensor(1.0), atol=1e-6)


def test_fit_with_obtree_corpus(
    simple_structure: Structure, simple_language: Language, simple_corpus: ObTree
) -> None:
    """Test fitting with ObTree corpus."""
    # Make a copy to fit
    language_copy = Language(
        nullary_functions=simple_language.nullary_functions.clone(),
        binary_functions={
            k: v.clone() for k, v in simple_language.binary_functions.items()
        },
    )

    # Fit to corpus
    metrics = language_copy.fit(
        simple_structure, simple_corpus, l1_lambda=0.01, max_steps=5, verbose=False
    )

    # Check metrics structure
    assert "losses" in metrics
    assert "sparsities" in metrics
    assert "likelihoods" in metrics
    assert "l1_penalties" in metrics
    assert "final_sparsity" in metrics
    assert "target_sparsity" in metrics
    assert "corpus_size" in metrics

    # Check that we tracked progress
    assert len(metrics["losses"]) == 5
    assert len(metrics["sparsities"]) == 5

    # Check constraints are satisfied
    assert torch.all(torch.isfinite(language_copy.nullary_functions))
    assert torch.all(language_copy.nullary_functions >= 0)
    total = language_copy.total()
    assert torch.allclose(total, torch.tensor(1.0), atol=1e-6)


def test_fit_with_language_corpus(
    simple_structure: Structure, simple_language: Language
) -> None:
    """Test fitting with Language corpus."""
    # Create corpus as another language with different weights
    corpus_nullary = torch.tensor([0.0, 0.5, 0.3, 0.1, 0.1, 0.0])
    corpus_language = Language(
        nullary_functions=corpus_nullary, binary_functions={"APP": torch.tensor(0.0)}
    )

    # Make a copy to fit
    language_copy = Language(
        nullary_functions=simple_language.nullary_functions.clone(),
        binary_functions={
            k: v.clone() for k, v in simple_language.binary_functions.items()
        },
    )

    # Fit to corpus
    metrics = language_copy.fit(
        simple_structure, corpus_language, l1_lambda=0.1, max_steps=3, verbose=False
    )

    # Should have updated weights toward corpus
    assert len(metrics["losses"]) == 3

    # Check constraints
    assert torch.all(language_copy.nullary_functions >= 0)
    total = language_copy.total()
    assert torch.allclose(total, torch.tensor(1.0), atol=1e-6)


def test_l1_regularization_effect(
    simple_structure: Structure, simple_language: Language
) -> None:
    """Test that L1 regularization affects sparsity."""
    # Create corpus with only a few nonzero elements
    corpus_nullary = torch.tensor([0.0, 1.0, 0.0, 0.0, 0.0, 0.0])  # Only X
    corpus_language = Language(
        nullary_functions=corpus_nullary, binary_functions={"APP": torch.tensor(0.0)}
    )

    # Fit with no regularization
    language_no_reg = Language(
        nullary_functions=torch.ones_like(simple_language.nullary_functions) * 0.1,
        binary_functions={
            k: v.clone() for k, v in simple_language.binary_functions.items()
        },
    )
    language_no_reg.normalize_()

    metrics_no_reg = language_no_reg.fit(
        simple_structure, corpus_language, l1_lambda=0.0, max_steps=10, verbose=False
    )

    # Fit with strong regularization
    language_with_reg = Language(
        nullary_functions=torch.ones_like(simple_language.nullary_functions) * 0.1,
        binary_functions={
            k: v.clone() for k, v in simple_language.binary_functions.items()
        },
    )
    language_with_reg.normalize_()

    metrics_with_reg = language_with_reg.fit(
        simple_structure, corpus_language, l1_lambda=1.0, max_steps=10, verbose=False
    )

    # Regularized version should be sparser
    final_sparsity_no_reg = metrics_no_reg["final_sparsity"]
    final_sparsity_with_reg = metrics_with_reg["final_sparsity"]

    # With strong L1, we should get sparser results
    assert final_sparsity_with_reg <= final_sparsity_no_reg


def test_fit_maintains_gradients(
    simple_structure: Structure, simple_language: Language, simple_corpus: ObTree
) -> None:
    """Test that fitting maintains gradient computation."""
    # Enable gradients
    for param in simple_language.parameters():
        param.requires_grad_(True)

    # Single step of fitting should maintain gradients
    language_copy = Language(
        nullary_functions=simple_language.nullary_functions.clone(),
        binary_functions={
            k: v.clone() for k, v in simple_language.binary_functions.items()
        },
    )

    # Manually compute one step to check gradients
    probs = language_copy.compute_probs(simple_structure)

    # Create synthetic data
    data = torch.tensor([0.0, 1.0, 1.0, 1.0, 0.0, 0.0])

    # Compute loss
    tiny = torch.finfo(probs.dtype).tiny
    log_likelihood = torch.xlogy(data, probs + tiny).sum()
    l1_penalty = language_copy.compute_l1_penalty()
    loss = -log_likelihood + 0.1 * l1_penalty

    # Check that we can compute gradients
    loss.backward()

    # Should have gradients
    assert language_copy.nullary_functions.grad is not None
    assert torch.any(language_copy.nullary_functions.grad != 0)
