import hypothesis
import pytest

from pomagma.reducer.graphred import B, abstract, as_graph, convert, is_linear
from pomagma.reducer.graphs import NVAR, Graph, Term
from pomagma.reducer.graphs_test import FUN_EXAMPLES, s_graphs
from pomagma.reducer.syntax import sexpr_parse
from pomagma.util.testing import for_each, xfail_if_not_implemented

CB = as_graph(lambda f, g, x: g(f(x)))

x = NVAR('x')
y = NVAR('y')


@for_each([
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
])
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


@pytest.mark.xfail
@hypothesis.given(s_graphs, s_graphs)
def test_app_runs(lhs, rhs):
    result = lhs(rhs)
    assert isinstance(result, Graph)


@for_each(FUN_EXAMPLES)
def test_abstract_fun(var, graph, expected):
    assert abstract(var, graph) is expected


@for_each([
    (
        x,
        x | x(x),
        Graph.make(
            Term.JOIN([1, 2]),
            Term.ABS(3),
            Term.ABS(4),
            Term.APP(5, 5),
            Term.VAR(2),
            Term.VAR(1),
        ),
    ),
])
def test_abstract(var, graph, expected):
    assert abstract(var, graph) is expected


@for_each([
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
            Term.JOIN([1, 2]),
            Term.ABS(3),
            Term.ABS(4),
            Term.APP(5, 5),
            Term.VAR(2),
            Term.VAR(1),
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
])
def test_as_graph(graph, expected):
    assert as_graph(graph) is expected
    assert as_graph(expected) is expected


@for_each([
    ('pair', lambda x, y, f: f(x, y)),
    ('copy', lambda x, y: x(y, y)),
    ('join', lambda x, y, z: x(y | z)),
    pytest.mark.xfail(('postconj', lambda r, s, f: f(B(r), B(s)))),
    pytest.mark.xfail(('preconj', lambda r, s, f: f(CB(r), CB(s)))),
    pytest.mark.xfail(
        ('conjugate', lambda r1, s1, r2, s2, f: f(B(r1, r2), B(s2, s1)))
    ),
])
def test_as_graph_runs(name, graph):
    print(name)
    actual = as_graph(graph)
    assert as_graph(actual) is actual


@for_each([
    'TOP',
    'BOT',
    'I',
    'K',
    'B',
    'C',
    'S',
    '(I K)',
    '(K I)',
    '(JOIN K (K I))',
    pytest.mark.xfail('(FUN x x 0 1)'),
])
def test_convert_runs(sexpr):
    term = sexpr_parse(sexpr)
    with xfail_if_not_implemented():
        graph = convert(term)
    assert isinstance(graph, Graph)
