from pomagma.reducer.code import I, K, B, C, S, VAR
from pomagma.reducer.sugar import app, join, abstract
import pytest

x = VAR('x')
y = VAR('y')
z = VAR('z')

ABSTRACT_EXAMPLES = [
    (x, x, I),
    (x, y, app(K, y)),
    (x, I, app(K, I)),
    (x, app(x, x), app(S, I, I)),
    (x, app(x, y), app(C, I, y)),
    (x, app(y, x), y),
    (x, app(y, app(z, x)), app(B, y, z)),
    (x, join(x, x), join(I, I)),
    (x, join(x, y), join(I, app(K, y))),
    (x, join(y, x), join(app(K, y), I)),
    (x, join(y, z), app(K, join(y, z))),
]


@pytest.mark.parametrize('var,body,expected_abs', ABSTRACT_EXAMPLES)
def test_abstract(var, body, expected_abs):
    actual_abs = abstract(var, body)
    assert actual_abs == expected_abs
