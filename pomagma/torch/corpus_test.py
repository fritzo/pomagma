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

    nullary_functions = Map({"X": Ob(1), "Y": Ob(2), "BOT": Ob(3)})
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

    stats = tree.stats
    expected_obs: Map[Ob, int] = Map({Ob(3): 1})
    expected_symbols: Map[str, int] = Map()

    assert stats.obs == expected_obs
    assert stats.symbols == expected_symbols


def test_obtree_str_representation() -> None:
    """Test string representation of ObTree."""
    # Test E-class representation
    obtree_ob = ObTree(ob=Ob(1))
    assert str(obtree_ob) == "[1]"

    # Test compound representation
    x = ObTree(ob=Ob(1))
    y = ObTree(ob=Ob(2))
    obtree_compound = ObTree(name="APP", args=(x, y))
    assert str(obtree_compound) == "APP [1] [2]"


def test_obtree_from_join(simple_structure: Structure) -> None:
    """Test ObTree.from_join method for finitary joins."""
    x = ObTree(ob=Ob(1))
    y = ObTree(ob=Ob(2))
    z = ObTree(name="APP", args=(x, y))

    # Test empty join (should try to return BOT, but BOT not defined in simple_structure)
    empty_join = ObTree.from_join(simple_structure, [])
    assert empty_join.ob == simple_structure.nullary_functions["BOT"]

    # Test singleton join (should return the single element)
    singleton_join = ObTree.from_join(simple_structure, [x])
    assert singleton_join is x

    # Test binary join (should create JOIN with frozenset)
    binary_join = ObTree.from_join(simple_structure, [x, y])
    assert binary_join.name == "JOIN"
    assert isinstance(binary_join.args, frozenset)
    assert binary_join.args == frozenset([x, y])

    # Test ternary join
    ternary_join = ObTree.from_join(simple_structure, [x, y, z])
    assert ternary_join.name == "JOIN"
    assert isinstance(ternary_join.args, frozenset)
    assert ternary_join.args == frozenset([x, y, z])


def test_obtree_finitary_join_stats(simple_structure: Structure) -> None:
    """Test that finitary joins are counted correctly in stats."""
    x = ObTree(ob=Ob(1))
    y = ObTree(ob=Ob(2))
    z = ObTree(name="APP", args=(x, y))

    # Test binary join stats (should count as 1 JOIN operation)
    binary_join = ObTree.from_join(simple_structure, [x, y])
    stats = binary_join.stats
    assert stats.symbols.get("JOIN") == 1  # 2-1 = 1
    assert stats.obs.get(Ob(1)) == 1
    assert stats.obs.get(Ob(2)) == 1

    # Test ternary join stats (should count as 2 JOIN operations)
    ternary_join = ObTree.from_join(simple_structure, [x, y, z])
    stats = ternary_join.stats
    assert stats.symbols.get("JOIN") == 2  # 3-1 = 2
    assert stats.obs.get(Ob(1)) == 2  # x appears in z and directly
    assert stats.obs.get(Ob(2)) == 2  # y appears in z and directly
    assert stats.symbols.get("APP") == 1  # from z

    # Test larger finitary join
    w = ObTree(ob=Ob(3))  # Assuming simple_structure has 3 items
    quad_join = ObTree.from_join(simple_structure, [x, y, z, w])
    stats = quad_join.stats
    assert stats.symbols.get("JOIN") == 3  # 4-1 = 3


def test_obtree_from_term_basic(simple_structure: Structure) -> None:
    """Test ObTree creation from basic Term."""
    from pomagma.reducer.syntax import FUN, NVAR, I

    # Test atom term
    tree = ObTree.from_term(simple_structure, I, strict=False)
    assert tree.name == "I"
    assert tree.args == ()

    # Test nominal abstraction term
    tree = ObTree.from_term(simple_structure, FUN(NVAR("x"), NVAR("x")), strict=False)
    assert tree.name == "I"
    assert tree.args == ()


def test_obtree_from_term_application(simple_structure: Structure) -> None:
    """Test ObTree creation from application Term."""
    from pomagma.reducer.syntax import APP, I, K

    # Test APP(I, K)
    app_term = APP(I, K)
    app_tree = ObTree.from_term(simple_structure, app_term, strict=False)

    assert app_tree.name == "APP"
    assert app_tree.args is not None
    assert isinstance(app_tree.args, tuple)
    assert len(app_tree.args) == 2
    assert app_tree.args[0].name == "I"
    assert app_tree.args[1].name == "K"


def test_obtree_from_term_with_e_classes(simple_structure: Structure) -> None:
    """Test ObTree creation from Term with unknown symbols."""
    from pomagma.reducer.syntax import APP, I, K

    # Create APP(I, K) where I and K are unknown to the simple_structure
    # This tests behavior when symbols don't resolve to E-classes in the structure
    app_term = APP(I, K)
    app_tree = ObTree.from_term(simple_structure, app_term, strict=False)

    # Should create an APP expression with atom arguments that don't resolve to E-classes
    assert app_tree.name == "APP"
    assert app_tree.args is not None
    assert isinstance(app_tree.args, tuple)
    assert len(app_tree.args) == 2
    assert app_tree.args[0].name == "I"
    assert app_tree.args[1].name == "K"


def test_obtree_from_term_stats(simple_structure: Structure) -> None:
    """Test stats computation for ObTree created from Term."""
    from pomagma.reducer.syntax import APP, JOIN, I, K

    # Create JOIN(I, APP(I, K))
    app_term = APP(I, K)
    join_term = JOIN(I, app_term)

    join_tree = ObTree.from_term(simple_structure, join_term, strict=False)
    stats = join_tree.stats

    # Should count symbols used in the term
    assert stats.symbols.get("JOIN") == 1
    assert stats.symbols.get("APP") == 1
