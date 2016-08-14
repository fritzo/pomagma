from pomagma.reducer.code import APP, TOP, BOT, I, K, B, C, S, J
from pomagma.reducer.code import sexpr_parse
from pomagma.reducer.de_bruijn import IVAR, abstract
from pomagma.reducer.de_bruijn import S_LINEAR_LOWER_BOUNDS
from pomagma.reducer.de_bruijn import S_LINEAR_UPPER_BOUNDS
from pomagma.reducer.de_bruijn import trool_all, trool_any
from pomagma.reducer.de_bruijn import try_decide_less
from pomagma.reducer.transforms import compile_
from pomagma.util.testing import for_each, xfail_if_not_implemented
import pytest

x = IVAR(0)
y = IVAR(1)
z = IVAR(2)

F = APP(K, I)
CI = APP(C, I)


def sexpr_compile(string):
    assert isinstance(string, str), string
    return compile_(sexpr_parse(string))


@for_each([
    (True, []),
    (True, [True]),
    (None, [None]),
    (False, [False]),
    (True, [True, True]),
    (None, [True, None]),
    (False, [True, False]),
    (None, [None, True]),
    (False, [None, False]),
    (None, [None, None]),
    (False, [False, True]),
    (False, [False, None]),
    (False, [False, False]),
])
def test_trool_all(expected, values):
    assert trool_all(values) == expected


@for_each([
    (False, []),
    (True, [True]),
    (None, [None]),
    (False, [False]),
    (True, [True, True]),
    (True, [True, None]),
    (True, [True, False]),
    (True, [None, True]),
    (None, [None, False]),
    (None, [None, None]),
    (True, [False, True]),
    (None, [False, None]),
    (False, [False, False]),
])
def test_trool_any(expected, values):
    assert trool_any(values) == expected


# ----------------------------------------------------------------------------
# Abstraction

# Note the lhs and rhs variable names are shifted by 1:
# lhs | rhs
# -------------------------
#   x | (should not occurr)
#   y | x
#   z | y
ABSTRACT_EXAMPLES = [
    (x, I),
    (y, APP(K, x)),
    (TOP, TOP),
    (BOT, BOT),
    (I, APP(K, I)),
    (APP(x, x), APP(APP(S, I), I)),
    (APP(x, y), APP(APP(C, I), x)),
    (APP(x, z), APP(APP(C, I), y)),
    (APP(y, x), x),
    (APP(z, x), y),
    (APP(y, APP(z, x)), APP(APP(B, x), y)),
    (J, APP(K, J)),
    (APP(J, y), APP(K, APP(J, x))),
    (APP(APP(J, y), z), APP(K, APP(APP(J, x), y))),
    (APP(J, x), J),
    (APP(APP(J, x), y), APP(J, x)),
    (APP(APP(J, y), x), APP(J, x)),
    (APP(APP(J, APP(z, x)), y), APP(APP(B, APP(J, x)), y)),
    (APP(APP(J, y), APP(z, x)), APP(APP(B, APP(J, x)), y)),
    (APP(APP(J, x), x), APP(APP(J, I), I)),
    (APP(APP(J, x), APP(z, x)), APP(APP(J, I), y)),
    (APP(APP(J, APP(y, x)), x), APP(APP(J, x), I)),
    (APP(APP(J, APP(y, x)), APP(z, x)), APP(APP(J, x), y)),
]


@for_each(ABSTRACT_EXAMPLES)
def test_abstract(body, expected):
    assert abstract(body) == expected


# ----------------------------------------------------------------------------
# Decision procedures

def box(x):
    return APP(CI, x)


_double = sexpr_compile('(FUN f (FUN x (f x x)))')


def double(x):
    return APP(_double, x)


TRY_DECIDE_LESS_EXAMPLES = [
    (True, BOT, TOP),
    (True, BOT, x),
    (True, x, TOP),
    (True, BOT, I),
    (True, I, TOP),
    (True, BOT, K),
    (True, BOT, F),
    (True, K, J),
    (True, F, J),
    (True, J, TOP),
    (False, TOP, BOT),
    (False, I, BOT),
    (False, TOP, I),
    (False, K, BOT),
    (False, F, BOT),
    (False, J, K),
    (False, J, F),
    (False, TOP, J),
    (True, box(BOT), box(TOP)),
    (True, box(BOT), box(x)),
    (True, box(x), box(TOP)),
    (True, box(BOT), box(I)),
    (True, box(I), box(TOP)),
    (True, box(BOT), box(K)),
    (True, box(BOT), box(F)),
    (True, box(K), box(J)),
    (True, box(F), box(J)),
    (True, box(J), box(TOP)),
    (False, box(TOP), box(BOT)),
    (False, box(I), box(BOT)),
    (False, box(TOP), box(I)),
    (False, box(K), box(BOT)),
    (False, box(F), box(BOT)),
    (False, box(J), box(K)),
    (False, box(J), box(F)),
    (False, box(TOP), box(J)),
    pytest.mark.xfail((True, double(BOT), double(TOP)), run=False),
    pytest.mark.xfail((True, double(BOT), double(x)), run=False),
    pytest.mark.xfail((True, double(x), double(TOP)), run=False),
    pytest.mark.xfail((True, double(BOT), double(I)), run=False),
    pytest.mark.xfail((True, double(I), double(TOP)), run=False),
    pytest.mark.xfail((True, double(BOT), double(K)), run=False),
    pytest.mark.xfail((True, double(BOT), double(F)), run=False),
    pytest.mark.xfail((True, double(K), double(J)), run=False),
    pytest.mark.xfail((True, double(F), double(J)), run=False),
    pytest.mark.xfail((True, double(J), double(TOP)), run=False),
    pytest.mark.xfail((False, double(TOP), double(BOT)), run=False),
    pytest.mark.xfail((False, double(I), double(BOT)), run=False),
    pytest.mark.xfail((False, double(TOP), double(I)), run=False),
    pytest.mark.xfail((False, double(K), double(BOT)), run=False),
    pytest.mark.xfail((False, double(F), double(BOT)), run=False),
    pytest.mark.xfail((False, double(J), double(K)), run=False),
    pytest.mark.xfail((False, double(J), double(F)), run=False),
    pytest.mark.xfail((False, double(TOP), double(J)), run=False),
]


@for_each(TRY_DECIDE_LESS_EXAMPLES)
def test_try_decide_less(expected, lhs, rhs):
    with xfail_if_not_implemented():
        actual = try_decide_less(lhs, rhs)
    assert actual == expected


INCOMPARABLES = [
    x, y, z,
    I, K, B, C, S,
    APP(K, I), APP(C, I), APP(C, B),
    APP(K, x), APP(B, x), APP(C, x), APP(S, x),
    APP(K, y), APP(B, y), APP(C, y), APP(S, y),
    APP(APP(B, x), y), APP(APP(C, x), y), APP(APP(S, x), y),
    APP(APP(B, y), z), APP(APP(C, y), z), APP(APP(S, y), z),
    APP(APP(B, z), x), APP(APP(C, z), x), APP(APP(S, z), x),
]

INCOMPARABLE_PAIRS = [
    (lhs is rhs, lhs, rhs)
    for lhs in INCOMPARABLES
    for rhs in INCOMPARABLES
]


@for_each(INCOMPARABLE_PAIRS)
def test_try_decide_less_incomparable(expected, lhs, rhs):
    with xfail_if_not_implemented():
        actual = try_decide_less(lhs, rhs)
    try:
        assert actual == expected
    except AssertionError as e:
        pytest.xfail(reason=str(e))


# ----------------------------------------------------------------------------
# Linear approximations of S

@for_each([
    (S_LINEAR_UPPER_BOUNDS[0], '(FUN x (FUN y (FUN z (x TOP (y z)))))'),
    (S_LINEAR_UPPER_BOUNDS[1], '(FUN x (FUN y (FUN z (x z (y TOP)))))'),
    (
        S_LINEAR_LOWER_BOUNDS[0],
        '(FUN x (FUN y (FUN z (J (x BOT (y z)) (x z (y BOT))))))',
    ),
])
def test_s_linear_bounds(actual, expected_sexpr):
    expected = sexpr_compile(expected_sexpr)
    assert actual == expected
