from pomagma.reducer.graphred import abstract, convert
from pomagma.reducer.graphs import Graph
from pomagma.reducer.graphs_test import FUN_EXAMPLES
from pomagma.reducer.syntax import sexpr_parse
from pomagma.util.testing import for_each, xfail_if_not_implemented


@for_each(FUN_EXAMPLES)
def test_abstract_fun(var, graph, expected):
    assert abstract(var, graph) is expected


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
