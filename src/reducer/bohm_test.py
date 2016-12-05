from pomagma.reducer.bohm import increment_rank, decrement_rank, is_const
from pomagma.reducer.bohm import substitute, app, abstract, join
from pomagma.reducer.code import TOP, BOT, NVAR, IVAR, APP, ABS, JOIN, QUOTE
from pomagma.util.testing import for_each, xfail_if_not_implemented

x = NVAR('x')
y = NVAR('y')
z = NVAR('z')


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


@for_each([
    (TOP, BOT, TOP),
    (BOT, TOP, BOT),
    (x, TOP, x),
    (IVAR(0), x, x),
    (IVAR(1), x, IVAR(0)),
    (IVAR(2), x, IVAR(1)),
    (APP(IVAR(0), IVAR(1)), x, APP(x, IVAR(0))),
    (ABS(IVAR(0)), x, ABS(IVAR(0))),
    (ABS(IVAR(1)), x, ABS(x)),
    (ABS(IVAR(2)), x, ABS(IVAR(1))),
    (JOIN(IVAR(0), IVAR(1)), x, JOIN(IVAR(0), x)),
])
def test_substitute(body, value, expected):
    assert substitute(body, value, 0) is expected


@for_each([
    (TOP, TOP, TOP),
    (TOP, BOT, TOP),
    (TOP, x, TOP),
    (BOT, TOP, BOT),
    (BOT, BOT, BOT),
    (BOT, x, BOT),
    (x, TOP, APP(x, TOP)),
    (x, BOT, APP(x, BOT)),
    (x, x, APP(x, x)),
    (IVAR(0), TOP, APP(IVAR(0), TOP)),
    (IVAR(0), BOT, APP(IVAR(0), BOT)),
    (IVAR(0), x, APP(IVAR(0), x)),
    (ABS(IVAR(1)), TOP, IVAR(0)),
    (ABS(IVAR(1)), BOT, IVAR(0)),
    (ABS(IVAR(1)), x, IVAR(0)),
    (ABS(IVAR(0)), TOP, TOP),
    (ABS(IVAR(0)), BOT, BOT),
    (ABS(IVAR(0)), x, x),
    (ABS(APP(IVAR(0), y)), TOP, TOP),
    (ABS(APP(IVAR(0), y)), BOT, BOT),
    (ABS(APP(IVAR(0), y)), x, APP(x, y)),
    (ABS(APP(IVAR(0), IVAR(1))), x, APP(x, IVAR(0))),
    (JOIN(x, y), z, JOIN(APP(x, z), APP(y, z))),
    (JOIN(ABS(IVAR(0)), x), TOP, TOP),
    (JOIN(ABS(IVAR(0)), x), BOT, APP(x, BOT)),
])
def test_app(fun, arg, expected):
    with xfail_if_not_implemented():
        assert app(fun, arg) is expected


@for_each([
    (TOP, TOP),
    (BOT, BOT),
    (x, ABS(x)),
    (IVAR(0), ABS(IVAR(0))),
    (IVAR(1), ABS(IVAR(1))),
    (APP(IVAR(0), x), ABS(APP(IVAR(0), x))),
    (APP(IVAR(0), IVAR(0)), ABS(APP(IVAR(0), IVAR(0)))),
    (APP(x, IVAR(0)), x),
    (JOIN(IVAR(0), x), JOIN(ABS(IVAR(0)), ABS(x))),
    (QUOTE(IVAR(0)), ABS(QUOTE(IVAR(0)))),
    (APP(QUOTE(IVAR(0)), IVAR(0)), QUOTE(IVAR(0))),
])
def test_abstract(code, expected):
    assert abstract(code) is expected


@for_each([
    (TOP, TOP, TOP),
    (TOP, BOT, TOP),
    (TOP, x, TOP),
    (TOP, IVAR(0), TOP),
    (BOT, TOP, TOP),
    (BOT, BOT, BOT),
    (BOT, x, x),
    (BOT, IVAR(0), IVAR(0)),
    (x, TOP, TOP),
    (x, BOT, x),
    (IVAR(0), TOP, TOP),
    (IVAR(0), BOT, IVAR(0)),
    (IVAR(0), IVAR(0), IVAR(0)),
    (x, y, JOIN(x, y)),
    (JOIN(x, y), x, JOIN(x, y)),
    (JOIN(x, y), y, JOIN(x, y)),
    (JOIN(x, y), z, JOIN(x, JOIN(y, z))),
    (JOIN(x, z), y, JOIN(x, JOIN(y, z))),
    (JOIN(y, z), x, JOIN(x, JOIN(y, z))),
    (JOIN(x, z), JOIN(x, y), JOIN(x, JOIN(y, z))),
])
def test_join(lhs, rhs, expected):
    assert join(lhs, rhs) is expected
