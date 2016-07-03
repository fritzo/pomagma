from pomagma.reducer import oracle
from pomagma.reducer.code import TOP, BOT, I, K, C, J
from pomagma.reducer.sugar import app
from pomagma.util.testing import for_each
import pytest

F = app(K, I)


def box(x):
    return app(C, I, x)


@for_each([
    (TOP, TOP, True),
    (TOP, BOT, False),
    (TOP, K, False),
    (TOP, F, False),
    (TOP, J, False),
    (BOT, TOP, False),
    (BOT, BOT, True),
    (BOT, K, False),
    (BOT, F, False),
    (BOT, J, False),
    (K, TOP, False),
    (K, BOT, False),
    (K, K, True),
    (K, F, False),
    (K, J, False),
    (F, TOP, False),
    (F, BOT, False),
    (F, K, False),
    (F, F, True),
    (F, J, False),
    (J, TOP, False),
    (J, BOT, False),
    (J, K, False),
    (J, F, False),
    (J, J, True),
    (box(TOP), box(TOP), True),
    (box(TOP), box(BOT), False),
    (box(TOP), box(I), False),
    (box(BOT), box(TOP), False),
    (box(BOT), box(BOT), True),
    (box(BOT), box(I), False),
    (box(I), box(TOP), False),
    (box(I), box(BOT), False),
    (box(I), box(I), True),
])
def test_try_decide_equal(x, y, expected):
    assert oracle.try_decide_equal(x, y) == expected


@for_each([
    (TOP, TOP, True),
    (TOP, BOT, False),
    (TOP, K, False),
    (TOP, F, False),
    (TOP, J, False),
    (BOT, TOP, True),
    (BOT, BOT, True),
    (BOT, K, True),
    (BOT, F, True),
    (BOT, J, True),
    (K, TOP, True),
    (K, BOT, False),
    (K, K, True),
    (K, F, False),
    pytest.mark.xfail((K, J, True)),
    (F, TOP, True),
    (F, BOT, False),
    (F, K, False),
    (F, F, True),
    pytest.mark.xfail((F, J, True)),
    (J, TOP, True),
    (J, BOT, False),
    (J, K, False),
    (J, F, False),
    (J, J, True),
    (box(TOP), box(TOP), True),
    (box(TOP), box(BOT), False),
    (box(TOP), box(I), False),
    (box(BOT), box(TOP), True),
    (box(BOT), box(BOT), True),
    (box(BOT), box(I), True),
    (box(I), box(TOP), True),
    (box(I), box(BOT), False),
    (box(I), box(I), True),
])
def test_try_decide_less(x, y, expected):
    assert oracle.try_decide_less(x, y) == expected
