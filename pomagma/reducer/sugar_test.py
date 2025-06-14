import pytest

from pomagma.reducer.bohm import KI, B, C, I, K, S
from pomagma.reducer.sugar import _compile, app, as_term, combinator, join_
from pomagma.reducer.syntax import NVAR, TOP
from pomagma.util.testing import for_each

f = NVAR("f")
x = NVAR("x")
y = NVAR("y")
z = NVAR("z")


TERM_EXAMPLES = [
    (I, I),
    (I(K), K),
    (K, K),
    (app(S, I, I), app(S, I, I)),
    (join_(K, I), join_(K, I)),
    (S(I, I), app(S, I, I)),
    (K | I, join_(K, I)),
    # (TOP(K | I), TOP),
]

CLOSED_FUN_EXAMPLES = [
    (lambda: x, x),
    (lambda: B, B),
    (lambda x: x, I),
    (lambda x, y: x, K),
    (lambda x, y: y, KI),
    (lambda x: lambda y: x, K),
    (lambda x: lambda x: x, KI),
    (lambda x, y, z: app(x, z, y), C),
    (lambda x, y, z: app(x, app(y, z)), B),
    (lambda x, y, z: app(x, z, app(y, z)), S),
    (lambda x: app(x, x), app(S, I, I)),
    (lambda x: app(f, app(x, x)), app(B, f, app(S, I, I))),
]

OPEN_FUN_EXAMPLES = [
    (lambda: x, x),
    (lambda x: y, app(K, y)),
    (lambda x: y, K(y)),
    (lambda x: app(f, x), f),
]


@for_each(CLOSED_FUN_EXAMPLES)
def test_compile_fun(arg, expected):
    actual = _compile(arg)
    assert actual == expected


@for_each(TERM_EXAMPLES)
def test_compile_term_raises_type_error(arg, expected):
    with pytest.raises(TypeError):
        _compile(arg)


@for_each(OPEN_FUN_EXAMPLES)
def test_combinator_must_be_closed(arg, expected):
    with pytest.raises(SyntaxError):
        combinator(arg).term


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


@for_each(
    [
        (div_rec_call, div_Y),
        (div_rec_app, div_Y),
    ]
)
def test_combinator_recursion(arg, expected):
    actual = arg.term
    assert actual == expected


@for_each(TERM_EXAMPLES + CLOSED_FUN_EXAMPLES + OPEN_FUN_EXAMPLES)
def test_as_term(arg, expected):
    actual = as_term(arg)
    assert actual == expected
