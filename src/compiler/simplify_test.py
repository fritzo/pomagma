from nose.tools import assert_equal
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.compiler.simplify import simplify
from pomagma.util.testing import for_each

NORMAL_EXAMPLES = [
    'APP K x',
    'APP x y',
    'B',
    'BOT',
    'C',
    'F',
    'HOLE',
    'I',
    'K',
    'S',
    'TOP',
    'W',
    'x',
]

NONNORMAL_EXAMPLES = [
    ('APP APP APP B x y z', 'APP x APP y z'),
    ('APP APP APP C x y z', 'APP APP x z y'),
    ('APP APP BOT x y', 'BOT'),
    ('APP APP F x y', 'y'),
    ('APP APP J BOT x', 'x'),
    ('APP APP J TOP x', 'TOP'),
    ('APP APP J x BOT', 'x'),
    ('APP APP J x TOP', 'TOP'),
    ('APP APP J x x', 'x'),
    ('APP APP J x y', 'JOIN x y'),
    ('APP APP K x y', 'x'),
    ('APP APP TOP x y', 'TOP'),
    ('APP BOT x', 'BOT'),
    ('APP COMP x y z', 'APP x APP y z'),
    ('APP F x', 'I'),
    ('APP I x', 'x'),
    ('APP TOP x', 'TOP'),
    ('CB', 'APP C B'),
    ('CI', 'APP C I'),
    ('JOIN BOT x', 'x'),
    ('JOIN TOP x', 'TOP'),
    ('JOIN x BOT', 'x'),
    ('JOIN x TOP', 'TOP'),
    ('JOIN x x', 'x'),
]


@for_each(NORMAL_EXAMPLES)
def normal_test(example):
    expected = parse_string_to_expr(example)
    actual = simplify(expected)
    assert_equal(actual, expected)


@for_each(NONNORMAL_EXAMPLES)
def simplify_test(example):
    term, expected = map(parse_string_to_expr, example)
    actual = simplify(term)
    assert_equal(actual, expected)