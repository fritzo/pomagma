from pomagma.reducer.bohm import (
    increment_rank, decrement_rank, is_const, is_linear,
    substitute, app, abstract, join, occurs, approximate_var, approximate,
    # try_prove_less_linear, try_prove_nless_linear,
    try_decide_less, is_normal, try_compute_step,
)
from pomagma.reducer.code import TOP, BOT, NVAR, IVAR, APP, ABS, JOIN, QUOTE
from pomagma.util.testing import for_each, xfail_if_not_implemented
import pytest

x = NVAR('x')
y = NVAR('y')
z = NVAR('z')


# ----------------------------------------------------------------------------
# Functional programming

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
    (TOP, True),
    (BOT, True),
    (x, True),
    (y, True),
    (IVAR(0), True),
    (IVAR(1), True),
    (APP(IVAR(0), IVAR(0)), True),
    (APP(IVAR(0), IVAR(1)), True),
    (APP(IVAR(1), IVAR(0)), True),
    (APP(IVAR(1), IVAR(1)), True),
    (ABS(APP(IVAR(0), IVAR(0))), False),
    (ABS(APP(IVAR(0), IVAR(1))), True),
    (ABS(APP(IVAR(1), IVAR(0))), True),
    (ABS(APP(IVAR(1), IVAR(1))), True),
    (ABS(JOIN(IVAR(0), APP(IVAR(0), x))), True),
    (ABS(JOIN(IVAR(0), APP(IVAR(0), IVAR(0)))), False),
    (QUOTE(ABS(APP(IVAR(0), IVAR(0)))), True),
])
def test_is_linear(code, expected):
    assert is_linear(code) is expected


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
    (QUOTE(IVAR(0)), x, QUOTE(IVAR(0))),
    (QUOTE(IVAR(1)), x, QUOTE(IVAR(1))),
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
    pytest.mark.xfail((JOIN(ABS(IVAR(0)), x), TOP, TOP)),
    (JOIN(ABS(IVAR(0)), x), BOT, APP(x, BOT)),
    (QUOTE(TOP), x, APP(QUOTE(TOP), x)),
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
    pytest.mark.xfail((JOIN(IVAR(0), x), JOIN(ABS(IVAR(0)), ABS(x)))),
    (QUOTE(IVAR(0)), ABS(QUOTE(IVAR(0)))),
    (APP(QUOTE(IVAR(0)), IVAR(0)), QUOTE(IVAR(0))),
])
def test_abstract(code, expected):
    assert abstract(code) is expected


# ----------------------------------------------------------------------------
# Scott ordering

@for_each([
    (TOP, 0, False),
    (TOP, 1, False),
    (BOT, 0, False),
    (BOT, 1, False),
    (x, 0, False),
    (x, 1, False),
    (y, 0, False),
    (y, 1, False),
    (IVAR(0), 0, True),
    (IVAR(0), 1, False),
    (IVAR(1), 0, False),
    (IVAR(1), 1, True),
    # TODO Add more examples.
])
def test_occurs(code, rank, expected):
    assert occurs(code, rank) is expected


APPROXIMATE_VAR_EXAMPLES = [
    (TOP, TOP, 0, [TOP]),
    (TOP, BOT, 0, [TOP]),
    (BOT, TOP, 0, [BOT]),
    (BOT, BOT, 0, [BOT]),
    (x, TOP, 0, [x]),
    (x, BOT, 0, [x]),
    (IVAR(0), TOP, 0, [IVAR(0), TOP]),
    (IVAR(0), BOT, 0, [IVAR(0), BOT]),
    # APP
    (
        APP(IVAR(0), IVAR(1)),
        TOP,
        0,
        [
            APP(IVAR(0), IVAR(1)),
            TOP,
        ],
    ),
    (
        APP(IVAR(0), IVAR(1)),
        BOT,
        0,
        [
            APP(IVAR(0), IVAR(1)),
            BOT,
        ],
    ),
    (
        APP(IVAR(1), IVAR(0)),
        TOP,
        0,
        [
            APP(IVAR(1), IVAR(0)),
            APP(IVAR(1), TOP),
        ],
    ),
    (
        APP(IVAR(1), IVAR(0)),
        BOT,
        0,
        [
            APP(IVAR(1), IVAR(0)),
            APP(IVAR(1), BOT),
        ],
    ),
    (
        APP(IVAR(0), IVAR(0)),
        TOP,
        0,
        [
            APP(IVAR(0), IVAR(0)),
            APP(IVAR(0), TOP),
            TOP,
        ],
    ),
    (
        APP(IVAR(0), IVAR(0)),
        BOT,
        0,
        [
            APP(IVAR(0), IVAR(0)),
            APP(IVAR(0), BOT),
            BOT,
        ],
    ),
    # JOIN
    (
        JOIN(IVAR(0), IVAR(1)),
        TOP,
        0,
        [
            JOIN(IVAR(0), IVAR(1)),
            TOP,
        ],
    ),
    (
        JOIN(IVAR(0), IVAR(1)),
        BOT,
        0,
        [
            JOIN(IVAR(0), IVAR(1)),
            IVAR(1),
        ],
    ),
    (
        JOIN(APP(x, IVAR(0)), APP(y, IVAR(0))),
        TOP,
        0,
        [
            JOIN(APP(x, IVAR(0)), APP(y, IVAR(0))),
            JOIN(APP(x, TOP), APP(y, IVAR(0))),
            JOIN(APP(x, IVAR(0)), APP(y, TOP)),
            JOIN(APP(x, TOP), APP(y, TOP)),
        ],
    ),
    # QUOTE
    (
        QUOTE(IVAR(0)),
        TOP,
        0,
        [QUOTE(IVAR(0))],
    )
]


@for_each(APPROXIMATE_VAR_EXAMPLES)
def test_approximate_var(code, direction, rank, expected):
    assert set(approximate_var(code, direction, rank)) == set(expected)


# TODO This is difficult to test, because the simplest argument that not
# is_cheap_to_copy is already very complex. We could mock, but that would
# pollute the memoized caches.
APPROXIMATE_EXAMPLES = [
    (IVAR(0), TOP, [IVAR(0)]),
    (IVAR(0), BOT, [IVAR(0)]),
    # TODO Add more examples.
]


@for_each(APPROXIMATE_EXAMPLES)
def test_approximate(code, direction, expected):
    assert set(approximate(code, direction)) == set(expected)


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


@for_each([
    (TOP, TOP, True),
    (TOP, BOT, False),
    (BOT, TOP, True),
    (BOT, BOT, True),
    (IVAR(0), IVAR(0), True),
    (IVAR(0), TOP, True),
    (IVAR(0), BOT, False),
    (TOP, IVAR(0), False),
    (BOT, IVAR(0), True),
    (IVAR(0), IVAR(1), False),
    (IVAR(1), IVAR(0), False),
])
def test_try_decide_less(lhs, rhs, expected):
    assert try_decide_less(lhs, rhs) is expected


# ----------------------------------------------------------------------------
# Computation

delta = ABS(APP(IVAR(0), IVAR(0)))

COMPUTE_EXAMPLES = [
    (TOP, None),
    (BOT, None),
    (IVAR(0), None),
    (IVAR(1), None),
    (IVAR(2), None),
    (delta, None),
    (APP(delta, delta), APP(delta, delta)),
    (APP(delta, APP(x, delta)), APP(APP(x, delta), APP(x, delta))),
]


@for_each(COMPUTE_EXAMPLES)
def test_is_normal(code, expected_try_compute_step):
    expected = (expected_try_compute_step is None)
    assert is_normal(code) is expected


@for_each(COMPUTE_EXAMPLES)
def test_try_compute_step(code, expected):
    with xfail_if_not_implemented():
        assert try_compute_step(code) is expected
