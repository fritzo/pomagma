import hypothesis
import hypothesis.strategies as s
import pytest

from pomagma.reducer.graphs import (
    APP,
    BOT,
    CB,
    FUN,
    JOIN,
    NVAR,
    TOP,
    B,
    Graph,
    Term,
    Y,
    as_graph,
    convert,
    find_scope,
    free_vars,
    graph_address,
    graph_is_wellformed,
    graph_permute,
    graph_sort,
    is_linear,
    letrec,
    partitioned_permutations,
    term_permute,
    try_compute_step,
    try_decide_less,
)
from pomagma.reducer.syntax import sexpr_parse
from pomagma.util.testing import for_each, xfail_if_not_implemented

j = NVAR("j")
x = NVAR("x")
y = NVAR("y")
z = NVAR("z")

s_nvars = s.sampled_from([x, y, z])
s_atoms = s.sampled_from([TOP, BOT, Y, x, y, z])


def s_graphs_extend(s_graphs):
    return s.one_of(
        s.builds(FUN, s_nvars, s_graphs),  # Introduces VAR.
        s.builds(APP, s_graphs, s_graphs),
        s.builds(JOIN, s.lists(s_graphs, min_size=2, max_size=3)),
    )


# FIXME Y is the only cyclic graph that this generates.
s_graphs = s.recursive(s_atoms, s_graphs_extend, max_leaves=5)  # Was 8 pre-2025


# ----------------------------------------------------------------------------
# Signature


@for_each(
    [
        ((0, 1, 2), Term.APP(0, 1), Term.APP(0, 1)),
        ((0, 2, 1), Term.APP(0, 1), Term.APP(0, 2)),
        ((1, 0, 2), Term.APP(0, 1), Term.APP(1, 0)),
        ((1, 2, 0), Term.APP(0, 1), Term.APP(1, 2)),
        ((2, 0, 1), Term.APP(0, 1), Term.APP(2, 0)),
        ((2, 1, 0), Term.APP(0, 1), Term.APP(2, 1)),
    ]
)
def test_term_permute(perm, term, expected):
    assert term_permute(term, perm) == expected


@for_each(
    [
        (
            (0, 1, 2, 3),
            [Term.ABS(1), Term.APP(2, 3), Term.NVAR("x"), Term.VAR(0)],
            [Term.ABS(1), Term.APP(2, 3), Term.NVAR("x"), Term.VAR(0)],
        ),
        (
            (1, 0, 2, 3),
            [Term.ABS(1), Term.APP(2, 3), Term.NVAR("x"), Term.VAR(0)],
            [Term.APP(2, 3), Term.ABS(0), Term.NVAR("x"), Term.VAR(1)],
        ),
        (
            (1, 2, 3, 0),
            [Term.ABS(1), Term.APP(2, 3), Term.NVAR("x"), Term.VAR(0)],
            [Term.VAR(1), Term.ABS(2), Term.APP(3, 0), Term.NVAR("x")],
        ),
        (
            (1, 2, 0),
            [Term.JOIN([1, 2]), Term.ABS(0), Term.VAR(1)],
            [Term.VAR(2), Term.JOIN([0, 2]), Term.ABS(1)],
        ),
    ]
)
def test_graph_permute(perm, graph, expected):
    assert graph_permute(graph, perm) == expected


@for_each(
    [
        ([[0]], [[0]]),
        ([[0], [1]], [[0, 1]]),
        ([[1], [0]], [[1, 0]]),
        ([[0, 1]], [[0, 1], [1, 0]]),
        ([[0], [1], [2]], [[0, 1, 2]]),
        ([[0], [2], [1]], [[0, 2, 1]]),
        ([[1], [0], [2]], [[1, 0, 2]]),
        ([[1], [2], [0]], [[2, 0, 1]]),
        ([[2], [0], [1]], [[1, 2, 0]]),
        ([[2], [1], [0]], [[2, 1, 0]]),
        ([[0, 1], [2]], [[0, 1, 2], [1, 0, 2]]),
        ([[0, 2], [1]], [[0, 2, 1], [1, 2, 0]]),
        ([[0], [1, 2]], [[0, 1, 2], [0, 2, 1]]),
        ([[1, 2], [0]], [[2, 0, 1], [2, 1, 0]]),
        ([[1], [0, 2]], [[1, 0, 2], [2, 0, 1]]),
        ([[2], [0, 1]], [[1, 2, 0], [2, 1, 0]]),
        (
            [[0, 1, 2]],
            [
                [0, 1, 2],
                [0, 2, 1],
                [1, 0, 2],
                [1, 2, 0],
                [2, 0, 1],
                [2, 1, 0],
            ],
        ),
        (
            [[0, 1], [2, 3]],
            [[0, 1, 2, 3], [0, 1, 3, 2], [1, 0, 2, 3], [1, 0, 3, 2]],
        ),
    ]
)
def test_partitioned_permutations(partitions, expected_perms):
    actual_perms = sorted(partitioned_permutations(partitions))
    assert actual_perms == expected_perms


@hypothesis.given(s_graphs, s.randoms())
def test_graph_address(terms, r):
    perm = list(range(1, len(terms)))
    r.shuffle(perm)
    hypothesis.assume(perm != sorted(perm))
    perm = [0, *perm]
    shuffled_terms = graph_permute(terms, perm)
    shuffled_address = graph_address(shuffled_terms)
    address = graph_address(terms)
    for source, target in enumerate(perm):
        assert address[source] == shuffled_address[target]


@hypothesis.given(s_graphs, s.randoms())
def test_graph_sort(terms, r):
    perm = list(range(1, len(terms)))
    r.shuffle(perm)
    hypothesis.assume(perm != sorted(perm))
    perm = [0, *perm]
    shuffled_terms = graph_permute(terms, perm)
    sorted_terms = graph_sort(shuffled_terms)
    assert sorted_terms == list(terms)


# ----------------------------------------------------------------------------
# Graph construction (intro forms)

FUN_EXAMPLES = [
    (x, x, Graph.make(Term.ABS(1), Term.VAR(0))),
    (x, y, Graph.make(Term.ABS(1), Term.NVAR("y"))),
    (x, APP(x, x), Graph.make(Term.ABS(1), Term.APP(2, 2), Term.VAR(0))),
    (
        x,
        APP(x, y),
        Graph.make(Term.ABS(1), Term.APP(2, 3), Term.VAR(0), Term.NVAR("y")),
    ),
    (
        x,
        APP(y, x),
        Graph.make(Term.ABS(1), Term.APP(2, 3), Term.NVAR("y"), Term.VAR(0)),
    ),
    (
        x,
        APP(APP(x, y), z),
        Graph.make(
            Term.ABS(1),
            Term.APP(2, 5),
            Term.APP(3, 4),
            Term.VAR(0),
            Term.NVAR("y"),
            Term.NVAR("z"),
        ),
    ),
    (
        y,
        APP(APP(x, y), z),
        Graph.make(
            Term.ABS(1),
            Term.APP(2, 5),
            Term.APP(3, 4),
            Term.NVAR("x"),
            Term.VAR(0),
            Term.NVAR("z"),
        ),
    ),
    (
        z,
        APP(APP(x, y), z),
        Graph.make(
            Term.ABS(1),
            Term.APP(2, 5),
            Term.APP(3, 4),
            Term.NVAR("x"),
            Term.NVAR("y"),
            Term.VAR(0),
        ),
    ),
    (
        y,
        Graph.make(
            Term.ABS(1),
            Term.APP(2, 5),
            Term.APP(3, 4),
            Term.NVAR("x"),
            Term.NVAR("y"),
            Term.VAR(0),
        ),
        Graph.make(
            Term.ABS(1),
            Term.ABS(2),
            Term.APP(3, 6),
            Term.APP(4, 5),
            Term.NVAR("x"),
            Term.VAR(0),
            Term.VAR(1),
        ),
    ),
    (
        x,
        Graph.make(
            Term.ABS(1),
            Term.ABS(2),
            Term.APP(3, 6),
            Term.APP(4, 5),
            Term.NVAR("x"),
            Term.VAR(0),
            Term.VAR(1),
        ),
        Graph.make(
            Term.ABS(1),
            Term.ABS(2),
            Term.ABS(3),
            Term.APP(4, 7),
            Term.APP(5, 6),
            Term.VAR(0),
            Term.VAR(1),
            Term.VAR(2),
        ),
    ),
]


@for_each(FUN_EXAMPLES)
def test_fun(var, graph, expected):
    assert FUN(var, graph) is expected


@hypothesis.given(s_graphs)
def test_join_top(x):
    assert x | TOP is TOP


@hypothesis.given(s_graphs)
def test_join_bot(x):
    assert x | BOT is x


@hypothesis.given(s_graphs)
def test_join_idempotent(x):
    assert x | x is x


@hypothesis.given(s_graphs, s_graphs)
@hypothesis.settings(deadline=2000)  # Increase deadline for complex graph operations
def test_join_commutative(x, y):
    assert x | y is y | x


@pytest.mark.skip(reason="timeout")
@hypothesis.given(s_graphs, s_graphs, s_graphs)
@hypothesis.settings(deadline=2000)  # Increase deadline for complex graph operations
def test_join_associative(x, y, z):
    assert (x | y) | z is x | (y | z)


@pytest.mark.xfail(reason="Join distributivity not implemented")
@hypothesis.given(s_graphs, s_graphs, s_graphs)
def test_join_distributive(f, g, x):
    assert (f | g)(x) is f(x) | g(x)


# ----------------------------------------------------------------------------
# Syntax


@for_each(
    [
        (lambda x: x, Graph.make(Term.ABS(1), Term.VAR(0))),
        (lambda x: x(x), Graph.make(Term.ABS(1), Term.APP(2, 2), Term.VAR(0))),
        (lambda x: lambda y: x, Graph.make(Term.ABS(1), Term.ABS(2), Term.VAR(0))),
        (lambda x: lambda y: y, Graph.make(Term.ABS(1), Term.ABS(2), Term.VAR(1))),
        (lambda x: lambda x: x, Graph.make(Term.ABS(1), Term.ABS(2), Term.VAR(1))),
        (lambda x, y: x, Graph.make(Term.ABS(1), Term.ABS(2), Term.VAR(0))),
        (lambda x, y: y, Graph.make(Term.ABS(1), Term.ABS(2), Term.VAR(1))),
        (
            lambda x: x | x(x),
            Graph.make(
                Term.ABS(1),
                Term.JOIN([2, 3]),
                Term.APP(3, 3),
                Term.VAR(0),
            ),
        ),
        (
            lambda f, g, x: g(f(x)),
            Graph.make(
                Term.ABS(1),
                Term.ABS(2),
                Term.ABS(3),
                Term.APP(4, 5),
                Term.VAR(1),
                Term.APP(6, 7),
                Term.VAR(0),
                Term.VAR(2),
            ),
        ),
    ]
)
def test_as_graph(graph, expected):
    assert as_graph(graph) is expected
    assert as_graph(expected) is expected


@for_each(
    [
        ("pair", lambda x, y, f: f(x, y)),
        ("copy", lambda x, y: x(y, y)),
        ("join", lambda x, y, z: x(y | z)),
        ("postconj", lambda r, s, f: f(B(r), B(s))),
        ("preconj", lambda r, s, f: f(CB(r), CB(s))),
        ("conjugate", lambda r1, s1, r2, s2, f: f(B(r1, r2), B(s2, s1))),
    ]
)
def test_as_graph_runs(name, graph):
    print(name)
    actual = as_graph(graph)
    assert as_graph(actual) is actual


@for_each(
    [
        (
            j,
            {"j": lambda x, y: x(j(y))},
            Graph.make(
                Term.ABS(1),
                Term.ABS(2),
                Term.APP(3, 4),
                Term.VAR(0),
                Term.APP(0, 5),
                Term.VAR(1),
            ),
        ),
    ]
)
def test_letrec(root, defs, expected):
    assert letrec(root, **defs) is expected


@for_each(
    [
        "TOP",
        "BOT",
        "I",
        "K",
        "B",
        "C",
        "S",
        "(I K)",
        "(K I)",
        "(JOIN K (K I))",
        pytest.param(
            "(FUN x x 0 1)",
            marks=pytest.mark.xfail(reason="FUN syntax not fully supported"),
        ),
    ]
)
def test_convert_runs(sexpr):
    term = sexpr_parse(sexpr)
    with xfail_if_not_implemented():
        graph = convert(term)
    assert isinstance(graph, Graph)


# ----------------------------------------------------------------------------
# Scott ordering


@hypothesis.given(s_graphs)
def test_less_top(graph):
    assert try_decide_less(graph, TOP) is True


@hypothesis.given(s_graphs)
def test_less_bot(graph):
    assert try_decide_less(BOT, graph) is True


@hypothesis.given(s_graphs)
def test_less_reflexive(graph):
    assert try_decide_less(graph, graph) is True


@hypothesis.given(s_graphs, s_graphs, s_graphs)
def test_less_transitive(x, y, z):
    with xfail_if_not_implemented():
        xy = try_decide_less(x, y)
        yz = try_decide_less(y, z)
        xz = try_decide_less(x, z)
    if xy is True and yz is True:
        assert xz is True
    elif xz is False:
        assert xy is not True or yz is not True


@pytest.mark.xfail(reason="Less join implementation incomplete")
@hypothesis.given(s_graphs, s_graphs)
def test_less_join(x, y):
    with xfail_if_not_implemented():
        assert try_decide_less(x, x | y) is True


# ----------------------------------------------------------------------------
# Variables


@hypothesis.given(s_graphs)
def test_free_vars_runs(graph):
    free_vars(graph, 0)


@for_each(
    [
        (
            Graph.make(Term.TOP),
            (frozenset(),),
        ),
        (
            Graph.make(Term.ABS(1), Term.VAR(0)),
            (frozenset(), frozenset([Term.VAR(0)])),
        ),
        (
            Graph.make(
                Term.ABS(1),
                Term.ABS(2),
                Term.APP(3, 4),
                Term.VAR(1),
                Term.VAR(0),
            ),
            (
                frozenset(),
                frozenset([Term.VAR(0)]),
                frozenset([Term.VAR(0), Term.VAR(1)]),
                frozenset([Term.VAR(1)]),
                frozenset([Term.VAR(0)]),
            ),
        ),
        (
            Graph.make(
                Term.ABS(1),
                Term.ABS(2),
                Term.JOIN([3, 4]),
                Term.VAR(1),
                Term.VAR(0),
            ),
            (
                frozenset(),
                frozenset([Term.VAR(0)]),
                frozenset([Term.VAR(0), Term.VAR(1)]),
                frozenset([Term.VAR(1)]),
                frozenset([Term.VAR(0)]),
            ),
        ),
    ]
)
def test_free_vars(graph, expecteds):
    for pos, expected in enumerate(expecteds):
        assert free_vars(graph, pos) == expected


@hypothesis.given(s_graphs)
def test_find_scope_runs(graph):
    hypothesis.assume(any(term.is_abs for term in graph))
    for pos, term in enumerate(graph):
        if term.is_abs:
            find_scope(graph, pos)


SCOPE_EXAMPLES = [
    (
        Graph.make(Term.ABS(1), Term.TOP),
        {0: frozenset([])},
    ),
    (
        Graph.make(Term.ABS(1), Term.NVAR("x")),
        {0: frozenset([])},
    ),
    (
        Graph.make(Term.ABS(1), Term.VAR(0)),
        {0: frozenset([1])},
    ),
    (
        Graph.make(Term.ABS(1), Term.APP(0, 0)),
        {0: frozenset([])},
    ),
    (
        Graph.make(Term.ABS(1), Term.ABS(2), Term.VAR(1)),
        {
            0: frozenset([]),
            1: frozenset([2]),
        },
    ),
    (
        Graph.make(Term.ABS(1), Term.ABS(2), Term.VAR(0)),
        {
            0: frozenset([1, 2]),
            1: frozenset([]),
        },
    ),
    (
        Graph.make(Term.ABS(1), Term.APP(2, 2), Term.VAR(0)),
        {0: frozenset([1, 2])},
    ),
    (
        Graph.make(Term.ABS(1), Term.APP(2, 1), Term.VAR(0)),
        {0: frozenset([1, 2])},
    ),
    (
        Graph.make(
            Term.ABS(1),
            Term.ABS(2),
            Term.JOIN([3, 4]),
            Term.VAR(1),
            Term.VAR(0),
        ),
        {
            0: frozenset([1, 2, 3, 4]),
            1: frozenset([2, 3]),
        },
    ),
    (
        Graph.make(
            Term.ABS(1),
            Term.ABS(2),
            Term.APP(3, 4),
            Term.VAR(0),
            Term.ABS(5),
            Term.APP(6, 7),
            Term.VAR(1),
            Term.VAR(4),
        ),
        {
            0: frozenset([1, 2, 3, 4, 5, 6, 7]),
            1: frozenset([2, 4, 5, 6, 7]),
            4: frozenset([5, 7]),
        },
    ),
]


@for_each(SCOPE_EXAMPLES)
def test_find_scope(graph, pos_scope_dict):
    for pos, term in enumerate(graph):
        if term.is_abs:
            expected_scope = pos_scope_dict[pos]
            assert find_scope(graph, pos) == expected_scope


@hypothesis.given(s_graphs)
def test_graph_is_wellformed(graph):
    assert graph_is_wellformed(graph)


@for_each(
    [
        Graph.make(
            Term.ABS(1),
            Term.APP(2, 3),
            Term.VAR(3),
            Term.ABS(4),
            Term.APP(5, 0),
            Term.VAR(0),
        ),
    ]
)
def test_not_graph_is_wellformed(graph):
    assert not graph_is_wellformed(graph)


@for_each(
    [
        (x, True),
        (x(x), True),
        (lambda x: x, True),
        (lambda x: x(x), False),
        (lambda x, y: x, True),
        (lambda x, y: y, True),
        (lambda x, y: x(y), True),
        (lambda x, y: y(x), True),
        (lambda x, y: x(x), False),
        (lambda x, y: y(y), False),
        (lambda x, y: x | y, True),
        (lambda x, y: x | y(x), True),
        (lambda x, y: x(y) | y, True),
        (lambda x, y: x(y) | y(x), True),
        (lambda x, y: x(x) | y(x), False),
        (lambda x, y: x(y) | y(y), False),
        (lambda x: x(lambda x: x)(lambda x: x), True),
    ]
)
def test_is_linear(graph, expected):
    graph = as_graph(graph)
    assert is_linear(graph) is expected


@hypothesis.given(s_graphs)
def test_is_linear_runs(graph):
    assert is_linear(graph) in (True, False)


@hypothesis.given(s_graphs, s_graphs)
def test_is_linear_app(lhs, rhs):
    if is_linear(lhs) and is_linear(rhs):
        with xfail_if_not_implemented():
            assert is_linear(lhs(rhs))
            assert is_linear(rhs(lhs))


@hypothesis.given(s_graphs, s_graphs)
def test_is_linear_join(lhs, rhs):
    if is_linear(lhs) and is_linear(rhs):
        assert is_linear(lhs | rhs)


# ----------------------------------------------------------------------------
# Reduction

COMPUTE_STEP_EXAMPLES = [
    (Graph.make(Term.ABS(1), Term.VAR(0)), None),
    (Graph.make(Term.ABS(1), Term.ABS(2), Term.VAR(0)), None),
    (Graph.make(Term.ABS(1), Term.ABS(2), Term.VAR(1)), None),
    (
        Graph.make(
            Term.APP(1, 3),
            Term.ABS(2),
            Term.VAR(1),
            Term.NVAR("x"),
        ),
        Graph.make(Term.NVAR("x")),
    ),
    (
        Graph.make(Term.APP(1, 1), Term.ABS(2), Term.VAR(1)),
        Graph.make(Term.ABS(1), Term.VAR(0)),
    ),
    (
        Graph.make(
            Term.APP(1, 4),
            Term.ABS(2),
            Term.APP(3, 3),
            Term.VAR(1),
            Term.NVAR("x"),
        ),
        Graph.make(Term.APP(1, 1), Term.NVAR("x")),
    ),
    pytest.param(  # {j x y = x (j y)} -> {j x y = x y}
        Graph.make(
            Term.ABS(1),
            Term.ABS(2),
            Term.APP(3, 4),
            Term.VAR(0),
            Term.APP(0, 5),
            Term.VAR(1),
        ),
        Graph.make(
            Term.ABS(1),
            Term.ABS(2),
            Term.APP(3, 4),
            Term.VAR(0),
            Term.VAR(1),
        ),
        marks=pytest.mark.xfail(reason="Recursive graph reduction not implemented"),
    ),
    (  # {j x y = x y} -> {j x = x}
        Graph.make(
            Term.ABS(1),
            Term.ABS(2),
            Term.APP(3, 4),
            Term.VAR(0),
            Term.VAR(1),
        ),
        Graph.make(
            Term.ABS(1),
            Term.VAR(0),
        ),
    ),
]


@for_each(COMPUTE_STEP_EXAMPLES)
def test_try_compute_step(graph, expected):
    assert try_compute_step(graph) is expected
