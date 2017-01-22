import hypothesis
import hypothesis.strategies as s

from pomagma.reducer.graphs import (ABS, APP, BOT, IVAR, JOIN, NVAR, TOP, Term,
                                    Y, graph_address, graph_permute,
                                    graph_sort, partitioned_permutations,
                                    term_permute)
from pomagma.util.testing import for_each


@for_each([
    ((0, 1, 2), Term.APP(0, 1), Term.APP(0, 1)),
    ((0, 2, 1), Term.APP(0, 1), Term.APP(0, 2)),
    ((1, 0, 2), Term.APP(0, 1), Term.APP(1, 0)),
    ((1, 2, 0), Term.APP(0, 1), Term.APP(1, 2)),
    ((2, 0, 1), Term.APP(0, 1), Term.APP(2, 0)),
    ((2, 1, 0), Term.APP(0, 1), Term.APP(2, 1)),
])
def test_term_permute(perm, term, expected):
    assert term_permute(term, perm) == expected


@for_each([
    (
        (0, 1, 2, 3),
        [Term.ABS(1), Term.APP(2, 3), Term.NVAR('x'), Term.IVAR(0)],
        [Term.ABS(1), Term.APP(2, 3), Term.NVAR('x'), Term.IVAR(0)],
    ),
    (
        (1, 0, 2, 3),
        [Term.ABS(1), Term.APP(2, 3), Term.NVAR('x'), Term.IVAR(0)],
        [Term.APP(2, 3), Term.ABS(0), Term.NVAR('x'), Term.IVAR(0)],
    ),
    (
        (1, 2, 3, 0),
        [Term.ABS(1), Term.APP(2, 3), Term.NVAR('x'), Term.IVAR(0)],
        [Term.IVAR(0), Term.ABS(2), Term.APP(3, 0), Term.NVAR('x')],
    ),
    (
        (1, 2, 0),
        [Term.JOIN([1, 2]), Term.ABS(0), Term.IVAR(0)],
        [Term.IVAR(0), Term.JOIN([0, 2]), Term.ABS(1)],
    ),
])
def test_graph_permute(perm, graph, expected):
    assert graph_permute(graph, perm) == expected


@for_each([
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
])
def test_partitioned_permutations(partitions, expected_perms):
    actual_perms = sorted(partitioned_permutations(partitions))
    assert actual_perms == expected_perms


# ----------------------------------------------------------------------------
# Property based tests

s_atoms = s.sampled_from([
    TOP,
    BOT,
    Y,
    NVAR('x'),
    NVAR('y'),
    NVAR('z'),
    IVAR(0),
    IVAR(1),
    IVAR(2),
])


def s_graphs_extend(s_graphs):
    return s.one_of(
        s.builds(ABS, s_graphs),
        s.builds(APP, s_graphs, s_graphs),
        s.builds(JOIN, s.lists(s_graphs, min_size=2, max_size=5)),
    )


# FIXME Y is the only cyclic graph that this generates.
s_graphs = s.recursive(s_atoms, s_graphs_extend, max_leaves=8)


@hypothesis.given(s_graphs, s.randoms())
def test_graph_address(terms, r):
    perm = range(1, len(terms))
    r.shuffle(perm)
    hypothesis.assume(perm != sorted(perm))
    perm = [0] + perm
    shuffled_terms = graph_permute(terms, perm)
    shuffled_address = graph_address(shuffled_terms)
    address = graph_address(terms)
    for source, target in enumerate(perm):
        assert address[source] == shuffled_address[target]


@hypothesis.given(s_graphs, s.randoms())
def test_graph_sort(terms, r):
    perm = range(1, len(terms))
    r.shuffle(perm)
    hypothesis.assume(perm != sorted(perm))
    perm = [0] + perm
    shuffled_terms = graph_permute(terms, perm)
    sorted_terms = graph_sort(shuffled_terms)
    assert sorted_terms == list(terms)


@hypothesis.given(s_graphs)
def test_join_top(x):
    assert JOIN([x, TOP]) is TOP


@hypothesis.given(s_graphs)
def test_join_bot(x):
    assert JOIN([x, BOT]) is x


@hypothesis.given(s_graphs)
def test_join_idempotent(x):
    assert JOIN([x, x]) is x


@hypothesis.given(s_graphs, s_graphs)
def test_join_commutative(x, y):
    assert JOIN([x, y]) is JOIN([y, x])


@hypothesis.given(s_graphs, s_graphs, s_graphs)
def test_join_associative(x, y, z):
    xy_z = JOIN([JOIN([x, y]), z])
    x_yz = JOIN([x, JOIN([y, z])])
    assert xy_z is x_yz
