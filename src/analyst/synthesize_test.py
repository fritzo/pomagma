import os
from nose.tools import assert_less
from nose.tools import assert_list_equal
from pomagma.analyst.synthesize import ComplexityEvaluator
from pomagma.analyst.synthesize import NaiveHoleFiller
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.language.util import dict_to_language
from pomagma.language.util import json_load
from pomagma.util import SRC
from pomagma.util.testing import for_each


VAR_NAMES = ['x', 'y', 'z']
LANGUAGE = dict_to_language(json_load(os.path.join(SRC, 'language/skj.json')))

evaluate_complexity = ComplexityEvaluator(LANGUAGE, VAR_NAMES)
fill_holes = NaiveHoleFiller(LANGUAGE, VAR_NAMES)

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


FILLINGS = sorted([
    'BOT', 'TOP',
    'I', 'K', 'CB', 'CI', 'J', 'B', 'C', 'W', 'S', 'Y', 'P', 'U', 'V',
])
FILLINGS += sorted(['APP HOLE HOLE', 'COMP HOLE HOLE'])
FILLINGS += sorted(['JOIN HOLE HOLE'])
FILLINGS += sorted(['x', 'y', 'z'])

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
