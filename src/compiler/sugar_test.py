from nose.tools import assert_equal
from pomagma.compiler.parser import parse_string_to_expr
from pomagma.compiler.sugar import desugar_expr
from pomagma.util.testing import for_each


EXAMPLES = [map(parse_string_to_expr, e) for e in [
    ('x', 'x'),
    ('FUN x x', 'I'),
    ('FUN x APP f x', 'f'),
    ('FIX x APP f x', 'APP Y f'),
    ('ABIND s r COMP r s', 'APP A CB'),
    ('FIXES BOOL I', 'EQUAL APP BOOL I I'),
]]


@for_each(EXAMPLES)
def test_desugar((expr, expected)):
    actual = desugar_expr(expr)
    assert_equal(actual, expected)
