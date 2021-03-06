from pomagma.compiler.parser import parse_string_to_expr as parse
from pomagma.util.testing import for_each_kwargs

EXAMPLES = [
    {
        'polish': 'x',
        'polish_vars': set(['x']),
        'polish_consts': set(),
        'polish_terms': set(['x']),
    },
    {
        'polish': 'TOP',
        'polish_vars': set(),
        'polish_consts': set(['TOP']),
        'polish_terms': set(['TOP']),
    },
    {
        'polish': 'APP TOP x',
        'polish_vars': set(['x']),
        'polish_consts': set(['TOP']),
        'polish_terms': set(['x', 'TOP', 'APP TOP x']),
    },
    {
        'polish': 'APP x TOP',
        'polish_vars': set(['x']),
        'polish_consts': set(['TOP']),
        'polish_terms': set(['x', 'TOP', 'APP x TOP']),
    },
    {
        'polish': 'LESS x TOP',
        'polish_vars': set(['x']),
        'polish_consts': set(['TOP']),
        'polish_terms': set(['x', 'TOP']),
    },
    {
        'polish': 'LESS APP TOP x y',
        'polish_vars': set(['x', 'y']),
        'polish_consts': set(['TOP']),
        'polish_terms': set(['x', 'y', 'TOP', 'APP TOP x']),
    },
]

for example in EXAMPLES:
    example['expression'] = parse(example['polish'])
    example['vars'] = set(map(parse, example['polish_vars']))
    example['consts'] = set(map(parse, example['polish_consts']))
    example['terms'] = set(map(parse, example['polish_terms']))


@for_each_kwargs(EXAMPLES)
def test_polish(expression, polish):
    assert expression.polish == polish


@for_each_kwargs(EXAMPLES)
def test_vars(expression, vars):
    assert set(expression.vars) == set(vars)


@for_each_kwargs(EXAMPLES)
def test_consts(expression, consts):
    assert set(expression.consts) == set(consts)


@for_each_kwargs(EXAMPLES)
def test_terms(expression, terms):
    assert set(expression.terms) == set(terms)
