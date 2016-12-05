from pomagma.reducer.bohm import increment_rank, decrement_rank, is_const
from pomagma.reducer.code import TOP, BOT, NVAR, IVAR, APP, ABS, JOIN, QUOTE
from pomagma.util.testing import for_each

x = NVAR('x')
y = NVAR('y')


@for_each([
    (TOP, 0, TOP),
    (BOT, 0, BOT),
    (x, 0, x),
    (y, 0, y),
    (IVAR(0), 0, IVAR(1)),
    (IVAR(1), 0, IVAR(2)),
    (IVAR(2), 0, IVAR(3)),
    (IVAR(0), 1, IVAR(0)),
    (IVAR(1), 1, IVAR(2)),
    (IVAR(2), 1, IVAR(3)),
    (IVAR(0), 2, IVAR(0)),
    (IVAR(1), 2, IVAR(1)),
    (IVAR(2), 2, IVAR(3)),
    (APP(IVAR(0), IVAR(1)), 0, APP(IVAR(1), IVAR(2))),
    (ABS(APP(IVAR(0), IVAR(0))), 0, ABS(APP(IVAR(0), IVAR(0)))),
    (ABS(APP(IVAR(1), IVAR(2))), 0, ABS(APP(IVAR(2), IVAR(3)))),
    (JOIN(IVAR(0), IVAR(1)), 0, JOIN(IVAR(1), IVAR(2))),
    (QUOTE(IVAR(0)), 0, QUOTE(IVAR(0))),
])
def test_increment_rank(code, min_rank, expected):
    assert increment_rank(code, min_rank) is expected


@for_each([
    (TOP, TOP),
    (BOT, BOT),
    (x, x),
    (y, y),
    (IVAR(1), IVAR(0)),
    (IVAR(2), IVAR(1)),
    (IVAR(3), IVAR(2)),
    (APP(IVAR(1), IVAR(2)), APP(IVAR(0), IVAR(1))),
    (ABS(APP(IVAR(0), IVAR(0))), ABS(APP(IVAR(0), IVAR(0)))),
    (ABS(APP(IVAR(2), IVAR(3))), ABS(APP(IVAR(1), IVAR(2)))),
    (JOIN(IVAR(1), IVAR(2)), JOIN(IVAR(0), IVAR(1))),
    (QUOTE(IVAR(0)), QUOTE(IVAR(0))),
])
def test_decrement_rank(code, expected):
    assert decrement_rank(code) is expected


@for_each([
    (TOP, True),
    (BOT, True),
    (x, True),
    (y, True),
    (IVAR(0), False),
    (IVAR(1), True),
    (IVAR(2), True),
    (IVAR(3), True),
    (APP(IVAR(0), IVAR(0)), False),
    (APP(IVAR(0), IVAR(1)), False),
    (APP(IVAR(1), IVAR(0)), False),
    (APP(IVAR(1), IVAR(2)), True),
    (ABS(APP(IVAR(0), IVAR(0))), True),
    (ABS(APP(IVAR(0), IVAR(1))), False),
    (ABS(APP(IVAR(1), IVAR(0))), False),
    (JOIN(IVAR(0), IVAR(0)), False),
    (JOIN(IVAR(0), IVAR(1)), False),
    (JOIN(IVAR(1), IVAR(0)), False),
    (JOIN(IVAR(1), IVAR(2)), True),
    (QUOTE(IVAR(0)), True),
])
def test_is_const(code, expected):
    assert is_const(code) is expected
