import pytest
import torch
from immutables import Map

from pomagma.torch.corpus import CorpusStats, ObTree
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
    binary_functions: Map[str, BinaryFunction] = Map(
        {"APP": BinaryFunction("APP", LRv, Vlr, Rvl, Lvr)}
    )

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
def simple_corpus_stats(simple_structure: Structure) -> CorpusStats:
    """Create a simple corpus as CorpusStats."""
    # Create corpus: X, Y, APP(X,Y)
    # This represents the counts from parsing "APP X Y"
    # X appears once, Y appears once, APP appears once
    # The result APP(X,Y) creates ob 3, so that appears once too
    obs = Map({Ob(1): 1, Ob(2): 1, Ob(3): 1})  # X, Y, APP(X,Y) result
    symbols = Map({"APP": 1})  # APP symbol appears once
    return CorpusStats(obs=obs, symbols=symbols)


@pytest.fixture
def simple_corpus(simple_structure: Structure) -> ObTree:
    """Create a simple corpus as an ObTree."""
    # Create corpus: X, Y, APP(X,Y)
    x_tree = ObTree(ob=Ob(1))  # X
    y_tree = ObTree(ob=Ob(2))  # Y
    return ObTree(name="APP", args=(x_tree, y_tree))


@pytest.fixture
def simple_corpus_data() -> torch.Tensor:
    """Create simple corpus data as tensor directly."""
    # Simple corpus with X=1, Y=1, APP(X,Y)=1 counts
    return torch.tensor([0.0, 1.0, 1.0, 1.0, 0.0, 0.0])  # X, Y, APP(X,Y) result


def test_warm_starting(simple_structure: Structure, simple_language: Language) -> None:
    """Test that warm starting reduces steps."""
    # First call without warm start
    probs1 = simple_language.compute_probs(simple_structure, reltol=1e-4)

    # Second call with warm start should be faster/same result
    probs2 = simple_language.compute_probs(
        simple_structure, reltol=1e-4, init_probs=probs1
    )

    # Results should be very close
    assert torch.allclose(probs1, probs2, atol=1e-6)


def test_minimum_steps(simple_structure: Structure, simple_language: Language) -> None:
    """Test minimum steps parameter."""
    # Test with min_steps=0 vs min_steps=5
    probs_min0 = simple_language.compute_probs(
        simple_structure,
        reltol=1e-1,  # High tolerance for quick convergence
        min_steps=0,
    )

    probs_min10 = simple_language.compute_probs(
        simple_structure,
        reltol=1e-1,  # High tolerance for quick convergence
        min_steps=10,
    )

    # Both should give valid results
    assert probs_min0.shape == probs_min10.shape
    assert torch.all(probs_min0 >= 0)
    assert torch.all(probs_min10 >= 0)


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


def test_fit_with_corpus_stats(
    simple_structure: Structure,
    simple_language: Language,
    simple_corpus_stats: CorpusStats,
) -> None:
    """Test fitting with CorpusStats corpus."""
    # Make a copy to fit
    language_copy = Language(
        nullary_functions=simple_language.nullary_functions.clone(),
        binary_functions={
            k: v.clone() for k, v in simple_language.binary_functions.items()
        },
    )

    # Fit to corpus
    losses = language_copy.fit(simple_structure, simple_corpus_stats, max_steps=5)

    # Check that we tracked progress
    assert len(losses) == 5

    # Check constraints are satisfied
    assert torch.all(torch.isfinite(language_copy.nullary_functions))
    assert torch.all(language_copy.nullary_functions >= 0)
    total = language_copy.total()
    assert torch.allclose(total, torch.tensor(1.0), atol=1e-6)


def test_fit_with_obtree_corpus(
    simple_structure: Structure, simple_language: Language, simple_corpus: ObTree
) -> None:
    """Test fitting with ObTree corpus (backwards compatibility)."""
    # Make a copy to fit
    language_copy = Language(
        nullary_functions=simple_language.nullary_functions.clone(),
        binary_functions={
            k: v.clone() for k, v in simple_language.binary_functions.items()
        },
    )

    # Convert ObTree to CorpusStats
    corpus_stats = simple_corpus.stats

    # Add a Bayesian prior in the form of pseudo-data
    prior_stats = CorpusStats(
        obs=Map({Ob(1): 1, Ob(2): 1, Ob(3): 1}), symbols=Map({"APP": 1})
    )
    stats = corpus_stats + prior_stats

    # Fit to corpus
    losses = language_copy.fit(simple_structure, stats, max_steps=5)

    # Check that we tracked progress
    assert len(losses) == 5

    # Check constraints are satisfied
    assert torch.all(torch.isfinite(language_copy.nullary_functions))
    assert torch.all(language_copy.nullary_functions >= 0)
    total = language_copy.total()
    assert torch.allclose(total, torch.tensor(1.0), atol=1e-6)


def test_fit_maintains_gradients(
    simple_structure: Structure,
    simple_language: Language,
    simple_corpus_stats: CorpusStats,
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
    loss = -log_likelihood

    # Check that we can compute gradients
    loss.backward()

    # Should have gradients
    assert language_copy.nullary_functions.grad is not None
    assert torch.any(language_copy.nullary_functions.grad != 0)


def test_iadd_corpus_with_corpus_stats(
    simple_structure: Structure,
    simple_language: Language,
    simple_corpus_stats: CorpusStats,
) -> None:
    """Test iadd_corpus with CorpusStats."""
    # Create empty language to add corpus to
    language_copy = simple_language.zeros_like()

    # Add corpus stats
    language_copy.iadd_corpus(simple_corpus_stats, weight=2.0)

    # Check that counts were added correctly with weight
    assert language_copy.nullary_functions[Ob(1)].item() == 2.0  # X
    assert language_copy.nullary_functions[Ob(2)].item() == 2.0  # Y
    assert language_copy.nullary_functions[Ob(3)].item() == 2.0  # APP(X,Y) result
    assert language_copy.binary_functions["APP"].item() == 2.0  # APP symbol


def test_complexity_with_string_input(
    simple_structure: Structure, simple_language: Language
) -> None:
    """Test complexity method with string input."""
    probs = simple_language.compute_probs(simple_structure)

    # Test with simple string expression
    complexity = simple_language.complexity(simple_structure, probs, "X")
    assert isinstance(complexity, float)
    assert complexity >= 0

    # Test with compound expression
    complexity_compound = simple_language.complexity(simple_structure, probs, "APP X Y")
    assert isinstance(complexity_compound, float)
    assert complexity_compound >= 0
    assert complexity_compound > complexity  # Compound should be more complex


def test_complexity_with_expression_input(
    simple_structure: Structure, simple_language: Language
) -> None:
    """Test complexity method with Expression input."""
    from pomagma.compiler.parser import parse_string_to_expr

    probs = simple_language.compute_probs(simple_structure)

    # Test with Expression
    expr = parse_string_to_expr("APP X Y")
    complexity = simple_language.complexity(simple_structure, probs, expr)
    assert isinstance(complexity, float)
    assert complexity >= 0


def test_complexity_with_obtree_input(
    simple_structure: Structure, simple_language: Language, simple_corpus: ObTree
) -> None:
    """Test complexity method with ObTree input."""
    probs = simple_language.compute_probs(simple_structure)

    # Test with ObTree
    complexity = simple_language.complexity(simple_structure, probs, simple_corpus)
    assert isinstance(complexity, float)
    assert complexity >= 0


def test_complexity_with_corpus_stats_input(
    simple_structure: Structure,
    simple_language: Language,
    simple_corpus_stats: CorpusStats,
) -> None:
    """Test complexity method with CorpusStats input."""
    probs = simple_language.compute_probs(simple_structure)

    # Test with CorpusStats
    complexity = simple_language.complexity(
        simple_structure, probs, simple_corpus_stats
    )
    assert isinstance(complexity, float)
    assert complexity >= 0


def test_complexity_input_equivalence(
    simple_structure: Structure, simple_language: Language
) -> None:
    """Test that different input types give the same complexity result."""
    from pomagma.compiler.parser import parse_string_to_expr

    probs = simple_language.compute_probs(simple_structure)

    # Create equivalent inputs
    string_input = "APP X Y"
    expr_input = parse_string_to_expr(string_input)
    obtree_input = ObTree.from_expr(simple_structure, expr_input)
    stats_input = obtree_input.stats

    # Compute complexity for each input type
    complexity_str = simple_language.complexity(simple_structure, probs, string_input)
    complexity_expr = simple_language.complexity(simple_structure, probs, expr_input)
    complexity_obtree = simple_language.complexity(
        simple_structure, probs, obtree_input
    )
    complexity_stats = simple_language.complexity(simple_structure, probs, stats_input)

    # All should give the same result
    assert abs(complexity_str - complexity_expr) < 1e-6
    assert abs(complexity_expr - complexity_obtree) < 1e-6
    assert abs(complexity_obtree - complexity_stats) < 1e-6


def test_complexity_backward_compatibility(
    simple_structure: Structure, simple_language: Language
) -> None:
    """Test that deprecated methods still work and give same results as new method."""
    from pomagma.compiler.parser import parse_string_to_expr

    probs = simple_language.compute_probs(simple_structure)

    # Test expression complexity
    expr = parse_string_to_expr("APP X Y")
    old_complexity = simple_language.expr_complexity(simple_structure, probs, expr)
    new_complexity = simple_language.complexity(simple_structure, probs, expr)
    assert abs(old_complexity - new_complexity) < 1e-6

    # Test obtree complexity
    obtree = ObTree.from_expr(simple_structure, expr)
    old_obtree_complexity = simple_language.obtree_complexity(
        simple_structure, probs, obtree
    )
    new_obtree_complexity = simple_language.complexity(simple_structure, probs, obtree)
    assert abs(old_obtree_complexity - new_obtree_complexity) < 1e-6


def test_complexity_handles_invalid_inputs(
    simple_structure: Structure, simple_language: Language
) -> None:
    """Test that complexity method handles edge cases appropriately."""
    probs = simple_language.compute_probs(simple_structure)

    # Test with zero probability (should return infinity)
    # Create a CorpusStats with an E-class that has zero probability
    zero_probs = probs.clone()
    zero_probs[1] = 0.0  # Make X (Ob(1)) have zero probability

    # Create a CorpusStats that directly references the zero-probability E-class
    zero_prob_stats = CorpusStats(obs=Map({Ob(1): 1}), symbols=Map())
    complexity = simple_language.complexity(
        simple_structure, zero_probs, zero_prob_stats
    )
    assert complexity == float("inf")

    # Test with unknown symbol (should handle gracefully)
    unknown_stats = CorpusStats(obs=Map(), symbols=Map({"UNKNOWN_SYMBOL": 1}))
    complexity_unknown = simple_language.complexity(
        simple_structure, probs, unknown_stats
    )
    assert isinstance(complexity_unknown, float)
    assert complexity_unknown >= 0


def test_language_iadd_corpus_finitary_joins() -> None:
    """Test that Language.iadd_corpus correctly handles finitary joins."""
    from pomagma.torch.corpus import ObTree
    from pomagma.torch.structure import (
        BinaryFunction,
        Ob,
        SparseBinaryFunction,
        SparseTernaryRelation,
    )

    # Create a minimal structure for testing
    item_count = 3
    nullary_functions = Map({"X": Ob(1), "Y": Ob(2), "Z": Ob(3)})

    # Create empty binary and symmetric function structures
    empty_table = SparseBinaryFunction(hash_table=torch.zeros(2, 3, dtype=torch.int32))
    empty_ternary = SparseTernaryRelation(
        torch.zeros(item_count + 2, dtype=torch.int32),
        torch.zeros((0, 2), dtype=torch.int32),
    )

    binary_functions: Map[str, BinaryFunction] = Map({})
    symmetric_functions = Map(
        {
            "JOIN": BinaryFunction(
                "JOIN", empty_table, empty_ternary, empty_ternary, empty_ternary
            )
        }
    )

    structure = Structure(
        name="test",
        item_count=item_count,
        nullary_functions=nullary_functions,
        binary_functions=binary_functions,
        symmetric_functions=symmetric_functions,
        unary_relations=Map(),
        binary_relations=Map(),
    )

    # Create a language
    language = Language(
        nullary_functions=torch.ones(item_count + 1),
        symmetric_functions=Map({"JOIN": torch.tensor(1.0)}),
    )

    # Create finitary join ObTrees
    x = ObTree(ob=Ob(1))
    y = ObTree(ob=Ob(2))
    z = ObTree(ob=Ob(3))

    # Test binary join
    binary_join = ObTree.from_join(structure, [x, y])
    binary_stats = binary_join.stats

    # Test ternary join
    ternary_join = ObTree.from_join(structure, [x, y, z])
    ternary_stats = ternary_join.stats

    # Add corpus stats to language
    initial_join_weight = language.symmetric_functions["JOIN"].item()

    language.iadd_corpus(binary_stats, weight=1.0)
    assert (
        language.symmetric_functions["JOIN"].item() == initial_join_weight + 1.0
    )  # 1 JOIN operation

    language.iadd_corpus(ternary_stats, weight=1.0)
    assert (
        language.symmetric_functions["JOIN"].item() == initial_join_weight + 1.0 + 2.0
    )  # +2 JOIN operations

    # Verify E-class counts are correct
    assert (
        language.nullary_functions[1].item() == 1.0 + 1.0 + 1.0
    )  # x appears in both joins
    assert (
        language.nullary_functions[2].item() == 1.0 + 1.0 + 1.0
    )  # y appears in both joins
    assert (
        language.nullary_functions[3].item() == 1.0 + 1.0
    )  # z appears only in ternary join
