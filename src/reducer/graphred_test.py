from pomagma.reducer.graphred import abstract, as_graph, convert
from pomagma.reducer.graphs import NVAR, Graph, Term
from pomagma.reducer.graphs_test import FUN_EXAMPLES
from pomagma.reducer.syntax import sexpr_parse
from pomagma.util.testing import for_each, xfail_if_not_implemented

x = NVAR('x')
y = NVAR('y')


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
])
def test_as_graph(graph, expected):
    assert as_graph(graph) is expected
    assert as_graph(expected) is expected


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
    '(FUN x x 0 1)',
])
def test_convert_runs(sexpr):
    term = sexpr_parse(sexpr)
    with xfail_if_not_implemented():
        graph = convert(term)
    assert isinstance(graph, Graph)
