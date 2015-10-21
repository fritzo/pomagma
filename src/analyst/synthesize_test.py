from nose.tools import assert_equal
from nose.tools import assert_less
from nose.tools import assert_list_equal
from pomagma.analyst.synthesize import ComplexityEvaluator
from pomagma.analyst.synthesize import NaiveHoleFiller
from pomagma.analyst.synthesize import simplify_defs
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.util.testing import for_each
from pomagma.util.testing import for_each_kwargs

FREE_VARS = map(parse_string_to_expr, ['x', 'y', 'z'])
LANGUAGE = {
    'APP': 1.0,
    'COMP': 1.6,
    'JOIN': 3.0,
    'B': 1.0,
    'C': 1.3,
    'I': 2.2,
    'K': 2.6,
    'S': 2.7,
    'BOT': 3.0,
    'TOP': 3.0,
    'x': 4.0,
    'y': 4.0,
    'z': 4.0,
}

evaluate_complexity = ComplexityEvaluator(LANGUAGE)
fill_holes = NaiveHoleFiller(LANGUAGE)

COMPLEXITY_EVALUATOR_EXAMPLES = [
    'B',
    'I',
    'APP I I',
    'APP x y',
    'COMP I I',
    'COMP x y',
    'JOIN I I',
    'JOIN x y',
    'x',
]


@for_each(COMPLEXITY_EVALUATOR_EXAMPLES)
def complexity_evaluator_test(example):
    term = parse_string_to_expr(example)
    assert_less(0, evaluate_complexity(term))


FILLINGS = sorted(
    ['BOT', 'TOP', 'I', 'K', 'B', 'C', 'S'] +
    ['APP HOLE HOLE', 'COMP HOLE HOLE', 'JOIN HOLE HOLE'] +
    ['x', 'y', 'z'])

HOLE_FILLER_EXAMPLES = [
    ('I', []),
    ('APP COMP S K I', []),
    ('HOLE', FILLINGS),
    ('APP K HOLE', ['APP K {}'.format(f) for f in FILLINGS]),
    ('APP HOLE K', ['APP {} K'.format(f) for f in FILLINGS]),
    ('APP HOLE HOLE', ['APP {} HOLE'.format(f) for f in FILLINGS] +
                      ['APP HOLE {}'.format(f) for f in FILLINGS]),
]


@for_each(HOLE_FILLER_EXAMPLES)
def hole_filler_test(example):
    term = parse_string_to_expr(example[0])
    expected = map(parse_string_to_expr, example[1])
    actual = list(fill_holes(term))
    assert_list_equal(actual, expected)


@for_each(HOLE_FILLER_EXAMPLES)
def hole_filler_increases_complexity_test(example):
    term = parse_string_to_expr(example[0])
    fillings = list(fill_holes(term))
    for f in fillings:
        assert_less(evaluate_complexity(term), evaluate_complexity(f))


SIMPLIFY_DEFS_EXAMPLES = [
    {
        'facts': [],
        'expected': [],
    },
    {
        'facts': ['EQUAL x y', 'LESS x APP x I'],
        'expected': ['LESS y APP y I'],
    },
    {
        'facts': ['EQUAL x APP y z', 'LESS x APP x I'],
        'expected': ['LESS APP y z APP APP y z I'],
    },
    {
        'facts': ['EQUAL a b', 'EQUAL b c', 'EQUAL c I', 'LESS I a'],
        'expected': ['LESS I I'],
    },
    {
        'facts': ['EQUAL x F', 'EQUAL x APP K I', 'NLESS x I'],
        'expected': ['NLESS F I', 'NLESS APP K I I'],
    },
]


@for_each_kwargs(SIMPLIFY_DEFS_EXAMPLES)
def simplify_defs_test(facts, expected):
    facts = set(map(parse_string_to_expr, facts))
    expected = set(map(parse_string_to_expr, expected))
    actual = simplify_defs(facts)
    assert_equal(actual, expected)
