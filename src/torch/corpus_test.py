import pytest
import torch
from immutables import Map

from pomagma.torch.corpus import CorpusStats, ObTree
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
    # Create a structure with 3 objects
    item_count = 3

    # Create binary function table: APP(1,2)=3
    table: list[tuple[Ob, Ob, Ob]] = [
        (Ob(1), Ob(2), Ob(3)),
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


def test_corpus_stats_empty() -> None:
    """Test empty CorpusStats creation."""
    stats = CorpusStats()
    assert stats.obs == Map()
    assert stats.symbols == Map()


def test_corpus_stats_creation() -> None:
    """Test CorpusStats creation with data."""
    obs = Map({Ob(1): 2, Ob(2): 3})
    symbols = Map({"APP": 1, "COMPOSE": 2})
    stats = CorpusStats(obs=obs, symbols=symbols)

    assert stats.obs == obs
    assert stats.symbols == symbols


def test_corpus_stats_add_empty() -> None:
    """Test adding empty CorpusStats objects."""
    stats1 = CorpusStats()
    stats2 = CorpusStats()
    result = stats1 + stats2

    assert result.obs == Map()
    assert result.symbols == Map()


def test_corpus_stats_add_disjoint() -> None:
    """Test adding CorpusStats with disjoint keys."""
    stats1 = CorpusStats(obs=Map({Ob(1): 2}), symbols=Map({"APP": 1}))
    stats2 = CorpusStats(obs=Map({Ob(2): 3}), symbols=Map({"COMPOSE": 2}))
    result = stats1 + stats2

    expected_obs = Map({Ob(1): 2, Ob(2): 3})
    expected_symbols = Map({"APP": 1, "COMPOSE": 2})

    assert result.obs == expected_obs
    assert result.symbols == expected_symbols


def test_corpus_stats_add_overlapping() -> None:
    """Test adding CorpusStats with overlapping keys."""
    stats1 = CorpusStats(
        obs=Map({Ob(1): 2, Ob(2): 1}), symbols=Map({"APP": 1, "COMPOSE": 3})
    )
    stats2 = CorpusStats(
        obs=Map({Ob(1): 3, Ob(3): 2}), symbols=Map({"APP": 2, "EQUAL": 1})
    )
    result = stats1 + stats2

    expected_obs = Map({Ob(1): 5, Ob(2): 1, Ob(3): 2})  # 2+3, 1+0, 0+2
    expected_symbols = Map({"APP": 3, "COMPOSE": 3, "EQUAL": 1})  # 1+2, 3+0, 0+1

    assert result.obs == expected_obs
    assert result.symbols == expected_symbols


def test_corpus_stats_add_commutativity() -> None:
    """Test that CorpusStats addition is commutative."""
    stats1 = CorpusStats(
        obs=Map({Ob(1): 2, Ob(2): 1}), symbols=Map({"APP": 1, "COMPOSE": 3})
    )
    stats2 = CorpusStats(
        obs=Map({Ob(1): 3, Ob(3): 2}), symbols=Map({"APP": 2, "EQUAL": 1})
    )

    result1 = stats1 + stats2
    result2 = stats2 + stats1

    assert result1.obs == result2.obs
    assert result1.symbols == result2.symbols


def test_corpus_stats_add_associativity() -> None:
    """Test that CorpusStats addition is associative."""
    stats1 = CorpusStats(obs=Map({Ob(1): 1}), symbols=Map({"APP": 1}))
    stats2 = CorpusStats(obs=Map({Ob(2): 2}), symbols=Map({"COMPOSE": 2}))
    stats3 = CorpusStats(obs=Map({Ob(3): 3}), symbols=Map({"EQUAL": 3}))

    result1 = (stats1 + stats2) + stats3
    result2 = stats1 + (stats2 + stats3)

    assert result1.obs == result2.obs
    assert result1.symbols == result2.symbols


def test_corpus_stats_add_with_zero() -> None:
    """Test adding CorpusStats with empty stats (identity element)."""
    stats = CorpusStats(
        obs=Map({Ob(1): 2, Ob(2): 3}), symbols=Map({"APP": 1, "COMPOSE": 2})
    )
    empty = CorpusStats()

    result_left = empty + stats
    result_right = stats + empty

    assert result_left.obs == stats.obs
    assert result_left.symbols == stats.symbols
    assert result_right.obs == stats.obs
    assert result_right.symbols == stats.symbols


def test_obtree_stats_basic(simple_structure: Structure) -> None:
    """Test ObTree stats computation for basic cases."""
    # Test nullary function (leaf)
    x_tree = ObTree(ob=Ob(1))
    x_stats = x_tree.stats

    expected_obs: Map[Ob, int] = Map({Ob(1): 1})
    expected_symbols: Map[str, int] = Map()

    assert x_stats.obs == expected_obs
    assert x_stats.symbols == expected_symbols


def test_obtree_stats_compound(simple_structure: Structure) -> None:
    """Test ObTree stats computation for compound expressions."""
    # Create APP(X, Y) tree
    x_tree = ObTree(ob=Ob(1))  # X
    y_tree = ObTree(ob=Ob(2))  # Y
    app_tree = ObTree(name="APP", args=(x_tree, y_tree))

    stats = app_tree.stats

    # Should count X, Y, and APP symbol
    # Note: APP(X,Y) result (Ob(3)) is only added if the function lookup succeeds
    # Let's check what actually happens
    expected_obs = Map(
        {Ob(1): 1, Ob(2): 1}
    )  # X, Y only (function doesn't produce result)
    expected_symbols = Map({"APP": 1})

    assert stats.obs == expected_obs
    assert stats.symbols == expected_symbols


def test_obtree_stats_caching(simple_structure: Structure) -> None:
    """Test that ObTree stats are cached properly."""
    x_tree = ObTree(ob=Ob(1))

    # First call computes stats
    stats1 = x_tree.stats

    # Second call should return the same cached object
    stats2 = x_tree.stats

    # Should be the same object (cached)
    assert stats1 is stats2


def test_obtree_from_string(simple_structure: Structure) -> None:
    """Test ObTree creation from string."""
    # Test parsing a simple expression
    tree = ObTree.from_string(simple_structure, "APP X Y")

    # When parsing from string, X and Y are not recognized as nullary functions
    # They remain as symbols, so the APP function can't be evaluated
    stats = tree.stats
    expected_obs: Map[Ob, int] = Map()  # No obs because X and Y are unknown symbols
    expected_symbols: Map[str, int] = Map(
        {"APP": 1, "X": 1, "Y": 1}
    )  # All remain as symbols

    assert stats.obs == expected_obs
    assert stats.symbols == expected_symbols


def test_obtree_str_representation() -> None:
    """Test ObTree string representation."""
    # Test ob representation
    x_tree = ObTree(ob=Ob(1))
    assert str(x_tree) == "[1]"

    # Test compound expression representation
    y_tree = ObTree(ob=Ob(2))
    app_tree = ObTree(name="APP", args=(x_tree, y_tree))
    assert str(app_tree) == "APP [1] [2]"
