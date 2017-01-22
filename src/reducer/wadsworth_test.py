from pomagma.reducer.wadsworth import Graph, convert
from pomagma.reducer.syntax import sexpr_parse
from pomagma.util.testing import for_each, xfail_if_not_implemented


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
    '(ABS x 0 1)',
])
def test_convert_runs(sexpr):
    term = sexpr_parse(sexpr)
    with xfail_if_not_implemented():
        graph = convert(term)
    assert isinstance(graph, Graph)
