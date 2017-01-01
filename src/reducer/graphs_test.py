from pomagma.reducer.graphs import (_ABS, _APP, _IVAR, _NVAR, graph_permute,
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
])
def test_graph_permute(perm, graph, expected):
    assert graph_permute(graph, perm) == expected
