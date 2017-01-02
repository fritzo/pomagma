from pomagma.reducer.syntax import sexpr_parse
from pomagma.reducer.klop import convert, is_graph
from pomagma.util.testing import for_each, xfail_if_not_implemented


@for_each([
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
    code = sexpr_parse(sexpr)
    with xfail_if_not_implemented():
        graph = convert(code)
    assert is_graph(graph)
