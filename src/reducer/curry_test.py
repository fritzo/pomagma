from pomagma.reducer.curry import abstract, convert, reduce, try_compute_step
from pomagma.reducer.syntax import (
    APP,
    BOT,
    IVAR,
    JOIN,
    NVAR,
    QUOTE,
    TOP,
    B,
    C,
    I,
    K,
    S,
    sexpr_parse,
)
from pomagma.reducer.testing import iter_equations
from pomagma.util.testing import for_each, xfail_if_not_implemented

a = NVAR("a")
b = NVAR("b")
c = NVAR("c")
w = NVAR("w")
x = NVAR("x")
y = NVAR("y")
z = NVAR("z")
i0 = IVAR(0)
i1 = IVAR(1)


@for_each(
    [
        (x, x, I),
        (x, y, APP(K, y)),
        (x, TOP, TOP),
        (x, BOT, BOT),
        (x, QUOTE(y), APP(K, QUOTE(y))),
        (x, I, APP(K, I)),
        (x, APP(x, x), APP(APP(S, I), I)),
        (x, APP(x, y), APP(APP(C, I), y)),
        (x, APP(y, x), y),
        (x, APP(y, APP(z, x)), APP(APP(B, y), z)),
        (x, JOIN(x, x), JOIN(I, I)),
        (x, JOIN(x, y), JOIN(I, APP(K, y))),
        (x, JOIN(y, x), JOIN(APP(K, y), I)),
        (x, JOIN(y, z), APP(K, JOIN(y, z))),
        (x, JOIN(APP(y, x), APP(z, x)), JOIN(y, z)),
    ]
)
def test_abstract(var, body, expected):
    actual = abstract(var, body)
    assert actual == expected


@for_each(
    [
        ("TOP", "TOP"),
        ("BOT", "BOT"),
        ("(FUN x x)", "I"),
        ("(FUN x TOP)", "TOP"),
        ("(FUN x BOT)", "BOT"),
        ("(FUN x (FUN y x))", "K"),
        ("(FUN x (FUN y (FUN z (x (y z)))))", "B"),
        ("(FUN x (FUN y (FUN z (x z y))))", "C"),
        ("(FUN x (FUN y (FUN z (x z (y z)))))", "S"),
    ]
)
def test_convert(term, expected):
    term = sexpr_parse(term)
    expected = sexpr_parse(expected)
    assert convert(term) is expected


NORMAL_EXAMPLES = [
    TOP,
    BOT,
    x,
    APP(x, y),
    APP(x, I),
    APP(x, K),
    APP(K, x),
    APP(B, x),
    APP(C, x),
    APP(S, x),
    APP(K, I),
    APP(APP(B, x), y),
    APP(APP(C, x), y),
    APP(APP(S, x), y),
]


@for_each(NORMAL_EXAMPLES)
def test_compute_step_normal(term):
    assert try_compute_step(term) is None


@for_each(NORMAL_EXAMPLES)
def test_reduce_normal(term):
    assert reduce(term) is term


COMPUTE_STEP_EXAMPLES = [
    (APP(TOP, x), TOP),
    (APP(BOT, x), BOT),
    (APP(I, x), x),
    (APP(APP(K, x), y), x),
    (APP(APP(APP(B, x), y), z), APP(x, APP(y, z))),
    (APP(APP(APP(C, x), y), z), APP(APP(x, z), y)),
    (APP(APP(APP(S, x), y), z), APP(APP(x, z), APP(y, z))),
]


@for_each(COMPUTE_STEP_EXAMPLES)
def test_try_compute_step(term, expected):
    assert try_compute_step(term) is expected


@for_each(COMPUTE_STEP_EXAMPLES)
def test_reduce_step(term, expected):
    assert reduce(term, 1) is expected


@for_each(iter_equations("curry"))
def test_reduce_equations(term, expected, message):
    with xfail_if_not_implemented():
        actual = reduce(term)
        expected = convert(expected)
    assert actual == expected, message
