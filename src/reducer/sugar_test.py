from pomagma.reducer.syntax import I, K, B, C, S, TOP, NVAR, APP
from pomagma.reducer.sugar import _compile
from pomagma.reducer.sugar import combinator, as_code, app, join_
from pomagma.util.testing import for_each
import pytest

f = NVAR('f')
x = NVAR('x')
y = NVAR('y')
z = NVAR('z')


CODE_EXAMPLES = [
    (I, I),
    (K, K),
    (app(S, I, I), app(S, I, I)),
]

CLOSED_FUN_EXAMPLES = [
    (lambda: x, x),
    (lambda: B, B),
    (lambda x: x, I),
    (lambda x, y: x, K),
    (lambda x, y: y, APP(K, I)),
    (lambda x: lambda y: x, K),
    (lambda x: lambda x: x, APP(K, I)),
    (lambda x, y, z: app(x, z, y), C),
    (lambda x, y, z: app(x, app(y, z)), B),
    (lambda x, y, z: app(x, z, app(y, z)), S),
    (lambda x: app(x, x), app(S, I, I)),
    (lambda x: app(f, app(x, x)), app(B, f, app(S, I, I))),
]

OPEN_FUN_EXAMPLES = [
    (lambda: x, x),
    (lambda x: y, app(K, y)),
    (lambda x: app(f, x), f),
]


@for_each(CLOSED_FUN_EXAMPLES)
def test_compile_fun(arg, expected):
    actual = _compile(arg)
    assert actual == expected


@for_each(CODE_EXAMPLES)
def test_compile_code_raises_type_error(arg, expected):
    with pytest.raises(TypeError):
        _compile(arg)


@for_each(OPEN_FUN_EXAMPLES)
def test_combinator_must_be_closed(arg, expected):
    with pytest.raises(SyntaxError):
        combinator(arg).code


@combinator
def Y(f):
    return app(lambda x: app(f, app(x, x)), lambda x: app(f, app(x, x)))


div_Y = Y(lambda f, x: join_(x, app(f, app(x, TOP))))


@combinator
def div_rec_call(x):
    return join_(x, div_rec_call(app(x, TOP)))


@combinator
def div_rec_app(x):
    return join_(x, app(div_rec_app, app(x, TOP)))


@for_each([
    (div_rec_call, div_Y),
    (div_rec_app, div_Y),
])
def test_combinator_recursion(arg, expected):
    actual = arg.code
    assert actual == expected


@for_each(CODE_EXAMPLES + CLOSED_FUN_EXAMPLES + OPEN_FUN_EXAMPLES)
def test_as_code(arg, expected):
    actual = as_code(arg)
    assert actual == expected
