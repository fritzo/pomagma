import hypothesis
import hypothesis.strategies as s
import pytest

from pomagma.reducer.graphs import (_ABS, _APP, _IVAR, _JOIN, _NVAR, ABS, APP,
                                    BOT, IVAR, JOIN, NVAR, TOP, graph_permute,
                                    term_permute)
from pomagma.util.testing import for_each


@for_each([
    ((0, 1, 2), (_APP, 0, 1), (_APP, 0, 1)),
    ((0, 2, 1), (_APP, 0, 1), (_APP, 0, 2)),
    ((1, 0, 2), (_APP, 0, 1), (_APP, 1, 0)),
    ((1, 2, 0), (_APP, 0, 1), (_APP, 1, 2)),
    ((2, 0, 1), (_APP, 0, 1), (_APP, 2, 0)),
    ((2, 1, 0), (_APP, 0, 1), (_APP, 2, 1)),
])
def test_term_permute(perm, term, expected):
    assert term_permute(term, perm) == expected


@for_each([
    (
        (0, 1, 2, 3),
        ((_ABS, 1), (_APP, 2, 3), (_NVAR, 'x'), (_IVAR, 0)),
        ((_ABS, 1), (_APP, 2, 3), (_NVAR, 'x'), (_IVAR, 0)),
    ),
    (
        (1, 0, 2, 3),
        ((_ABS, 1), (_APP, 2, 3), (_NVAR, 'x'), (_IVAR, 0)),
        ((_APP, 2, 3), (_ABS, 0), (_NVAR, 'x'), (_IVAR, 0)),
    ),
    (
        (1, 2, 3, 0),
        ((_ABS, 1), (_APP, 2, 3), (_NVAR, 'x'), (_IVAR, 0)),
        ((_IVAR, 0), (_ABS, 2), (_APP, 3, 0), (_NVAR, 'x')),
    ),
    (
        (1, 2, 0),
        ((_JOIN, frozenset([1, 2])), (_ABS, 0), (_IVAR, 0)),
        ((_IVAR, 0), (_JOIN, frozenset([0, 2])), (_ABS, 1)),
    ),
])
def test_graph_permute(perm, graph, expected):
    assert graph_permute(graph, perm) == expected


# ----------------------------------------------------------------------------
# Property based tests

s_atoms = s.sampled_from([
    TOP,
    BOT,
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
        s.builds(JOIN, s.frozensets(s_graphs, max_size=4, average_size=2)),
    )


s_graphs = s.recursive(s_atoms, s_graphs_extend, max_leaves=3)


@pytest.mark.xfail
@hypothesis.given(s_graphs)
def test_join_top(x):
    assert JOIN(frozenset([x, TOP])) is TOP


@pytest.mark.xfail
@hypothesis.given(s_graphs)
def test_join_bot(x):
    assert JOIN(frozenset([x, BOT])) is x


@hypothesis.given(s_graphs)
def test_join_idempotent(x):
    assert JOIN(frozenset([x])) is x


@hypothesis.given(s_graphs, s_graphs)
def test_join_commutative(x, y):
    assert JOIN(frozenset([x, y])) is JOIN(frozenset([y, x]))


@pytest.mark.xfail
@hypothesis.given(s_graphs, s_graphs, s_graphs)
def test_join_associative(x, y, z):
    xy_z = JOIN(frozenset([JOIN(frozenset([x, y])), z]))
    x_yz = JOIN(frozenset([x, JOIN(frozenset([y, z]))]))
    assert xy_z is x_yz
