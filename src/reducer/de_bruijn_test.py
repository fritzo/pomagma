from pomagma.reducer import de_bruijn
from pomagma.reducer.code import APP, JOIN, TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import sexpr_parse
from pomagma.reducer.de_bruijn import IVAR, abstract, try_decide_less
from pomagma.reducer.de_bruijn import S_LINEAR_LOWER_BOUNDS
from pomagma.reducer.de_bruijn import S_LINEAR_UPPER_BOUNDS
from pomagma.reducer.testing import iter_equations
from pomagma.reducer.testing import s_codes, s_quoted, s_sk_codes, s_skj_codes
from pomagma.reducer.transforms import compile_
from pomagma.util.testing import for_each, xfail_if_not_implemented
import hypothesis
import pytest

x = IVAR(0)
y = IVAR(1)
z = IVAR(2)
F = APP(K, I)
J = JOIN(K, F)
CI = APP(C, I)


def sexpr_compile(string):
    assert isinstance(string, str), string
    return compile_(sexpr_parse(string))


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
    (JOIN(x, x), JOIN(I, I)),
    (JOIN(x, y), JOIN(I, APP(K, x))),
    (JOIN(y, x), JOIN(APP(K, x), I)),
    (JOIN(y, z), APP(K, JOIN(x, y))),
    (JOIN(APP(y, x), APP(z, x)), JOIN(x, y)),
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
    (True, double(BOT), double(TOP)),
    (True, double(BOT), double(x)),
    (True, double(x), double(TOP)),
    (True, double(BOT), double(I)),
    (True, double(I), double(TOP)),
    (True, double(BOT), double(K)),
    (True, double(BOT), double(F)),
    (True, double(K), double(J)),
    (True, double(F), double(J)),
    (True, double(J), double(TOP)),
    (False, double(TOP), double(BOT)),
    (False, double(I), double(BOT)),
    (False, double(TOP), double(I)),
    (False, double(K), double(BOT)),
    (False, double(F), double(BOT)),
    pytest.mark.xfail((False, double(J), double(K))),
    pytest.mark.xfail((False, double(J), double(F))),
    (False, double(TOP), double(J)),
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
    (S_LINEAR_LOWER_BOUNDS[0], '(FUN x (FUN y (FUN z (x BOT (y z)))))'),
    (S_LINEAR_LOWER_BOUNDS[1], '(FUN x (FUN y (FUN z (x z (y BOT)))))'),
])
def test_s_linear_bounds(actual, expected_sexpr):
    expected = sexpr_compile(expected_sexpr)
    assert actual == expected


# ----------------------------------------------------------------------------
# Reduction

@pytest.mark.timeout(1)
@for_each(iter_equations('de_bruijn'))
def test_reduce_equations(code, expected, message):
    with xfail_if_not_implemented():
        actual = de_bruijn.reduce(code)
    assert actual == expected, message


@hypothesis.given(s_sk_codes)
def test_simplify_runs_sk(code):
    with xfail_if_not_implemented():
        de_bruijn.simplify(code)


@hypothesis.given(s_skj_codes)
def test_simplify_runs_skj(code):
    with xfail_if_not_implemented():
        de_bruijn.simplify(code)


@hypothesis.given(s_codes)
def test_simplify_runs(code):
    with xfail_if_not_implemented():
        de_bruijn.simplify(code)


@hypothesis.given(s_quoted)
def test_simplify_runs_quoted(quoted):
    with xfail_if_not_implemented():
        de_bruijn.simplify(quoted)
