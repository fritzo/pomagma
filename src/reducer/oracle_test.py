from pomagma.reducer import oracle
from pomagma.reducer.code import TOP, BOT, I, K, B, C, J
from pomagma.reducer.sugar import app
from pomagma.util.testing import for_each
import pytest

F = app(K, I)


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
    (BOT, BOT),
    (K, TOP),
    (F, TOP),
    (J, TOP),
    (app(B, K, app(C, I, TOP)), TOP),
    pytest.mark.xfail((app(B, K, app(C, I, BOT)), I)),
])
def test_try_cast_unit(x, expected):
    assert oracle.try_cast_unit(x) == expected


@for_each([
    (TOP, TOP),
    (BOT, BOT),
    (K, K),
    (F, F),
    (BOT, BOT),
    (I, TOP),
    (J, TOP),
])
def test_try_cast_bool(x, expected):
    assert oracle.try_cast_bool(x) == expected
