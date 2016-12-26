import pytest

from pomagma.reducer.engines import oracle
from pomagma.reducer.syntax import (APP, BOT, JOIN, NVAR, QAPP, QQUOTE, QUOTE,
                                    TOP, B, C, I, K)
from pomagma.util.testing import for_each

F = APP(K, I)
J = JOIN(K, F)
x = NVAR('x')
y = NVAR('y')


def app(*args):
    result = args[0]
    for arg in args[1:]:
        result = APP(result, arg)
    return result


def box(x):
    return app(C, I, x)


ORDER_EXAMPLES = [
    (TOP, TOP, True, True),
    (TOP, BOT, False, True),
    (TOP, I, False, True),
    (TOP, K, False, True),
    (TOP, F, False, True),
    (TOP, J, False, True),
    (BOT, BOT, True, True),
    (BOT, I, True, False),
    (BOT, K, True, False),
    (BOT, F, True, False),
    (BOT, J, True, False),
    (I, I, True, True),
    (I, K, False, False),
    (I, F, False, False),
    (I, J, False, False),
    (K, K, True, True),
    (K, F, False, False),
    (K, J, True, False),
    (F, F, True, True),
    (F, J, True, False),
    (J, J, True, True),
    (box(TOP), box(TOP), True, True),
    (box(TOP), box(BOT), False, True),
    (box(TOP), box(I), False, True),
    (box(TOP), box(K), False, True),
    (box(TOP), box(F), False, True),
    (box(TOP), box(J), False, True),
    (box(BOT), box(BOT), True, True),
    (box(BOT), box(I), True, False),
    (box(BOT), box(K), True, False),
    (box(BOT), box(F), True, False),
    (box(BOT), box(J), True, False),
    (box(I), box(I), True, True),
    (box(I), box(K), False, False),
    (box(I), box(F), False, False),
    (box(I), box(J), False, False),
    (box(K), box(K), True, True),
    (box(K), box(F), False, False),
    (box(K), box(J), True, False),
    (box(F), box(F), True, True),
    (box(F), box(J), True, False),
    (box(J), box(J), True, True),
    pytest.mark.xfail((I, app(B, K, app(C, I, TOP)), True, False)),
    pytest.mark.xfail((I, app(B, K, app(C, I, BOT)), False, True)),
]


@for_each(ORDER_EXAMPLES)
def test_try_decide_less(x, y, less_xy, less_yx):
    assert oracle.try_decide_less(x, y) == less_xy
    assert oracle.try_decide_less(y, x) == less_yx


@for_each(ORDER_EXAMPLES)
def test_try_decide_equal(x, y, less_xy, less_yx):
    assert oracle.try_decide_equal(x, y) == (less_xy and less_yx)
    assert oracle.try_decide_equal(y, x) == (less_xy and less_yx)


@for_each([
    (TOP, TOP),
    (BOT, BOT),
    (I, I),
    (K, TOP),
    (F, TOP),
    (J, TOP),
    (app(B, K, app(C, I, TOP)), TOP),
    pytest.mark.xfail((app(B, K, app(C, I, BOT)), I)),
    (x, None),
])
def test_try_cast_unit(x, expected):
    assert oracle.try_cast_unit(x) == expected


@for_each([
    (TOP, TOP),
    (BOT, BOT),
    (K, K),
    (F, F),
    (I, TOP),
    (J, TOP),
    (x, None),
])
def test_try_cast_bool(x, expected):
    assert oracle.try_cast_bool(x) == expected


none = K


def some(x):
    return app(K, app(C, I, x))


@for_each([
    (TOP, TOP),
    (BOT, BOT),
    (none, none),
    (some(TOP), some(TOP)),
    (some(BOT), some(BOT)),
    (some(I), some(I)),
    (some(K), some(K)),
    (some(F), some(F)),
    pytest.mark.xfail((JOIN(some(K), some(F)), some(J))),
    (app(J, none, some(BOT)), TOP),
    (I, TOP),
    (F, TOP),
    (J, TOP),
    (x, None),
])
def test_try_cast_maybe(x, expected):
    assert oracle.try_cast_maybe(x) == expected


@for_each([
    (TOP, TOP),
    (BOT, BOT),
    (QUOTE(x), QUOTE(x)),
    (app(QQUOTE, x), app(QQUOTE, x)),
    (app(QAPP, x, y), app(QAPP, x, y)),
    (x, None),
])
def test_try_cast_code(x, expected):
    assert oracle.try_cast_code(x) == expected
