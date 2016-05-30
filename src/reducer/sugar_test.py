from pomagma.reducer.code import I, K, B, C, S, VAR, APP
from pomagma.reducer.sugar import abstract, as_code, app, join
import pytest

f = VAR('f')
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


Yf = app((lambda x: app(f, app(x, x))), (lambda x: app(f, app(x, x))))


def fix_f(x):
    return app(f, app(fix_f, x))


AS_CODE_EXAMPLES = [
    (I, I),
    (K, K),
    (app(S, I, I), app(S, I, I)),
    (lambda x: x, I),
    (lambda x, y: x, K),
    (lambda x, y: y, APP(K, I)),
    (lambda x: lambda y: x, K),
    (lambda x: lambda x: x, APP(K, I)),
    (lambda x, y, z: app(x, z, y), C),
    (lambda x, y, z: app(x, app(y, z)), B),
    (lambda x, y, z: app(x, z, app(y, z)), S),
    pytest.mark.xfail((fix_f, Yf)),
]


@pytest.mark.parametrize('arg,expected_code', AS_CODE_EXAMPLES)
def test_as_code(arg, expected_code):
    actual_code = as_code(arg)
    assert actual_code == expected_code
