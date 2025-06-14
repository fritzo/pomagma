from pomagma.reducer.pattern import match
from pomagma.reducer.syntax import ABS, APP, IVAR, JOIN, NVAR, QUOTE, TOP
from pomagma.util.testing import for_each

x = NVAR("x")
y = NVAR("y")


@for_each(
    [
        (TOP, TOP, {}),
        (TOP, x, None),
        (x, x, {x: x}),
        (x, TOP, {x: TOP}),
        (y, TOP, {y: TOP}),
        (x, y, {x: y}),
        (IVAR(0), x, None),
        (ABS(APP(IVAR(0), x)), ABS(APP(IVAR(0), IVAR(0))), None),
        (ABS(APP(IVAR(1), x)), ABS(APP(IVAR(1), IVAR(0))), None),
        (ABS(APP(IVAR(0), x)), ABS(APP(IVAR(0), IVAR(1))), {x: IVAR(0)}),
        (ABS(APP(IVAR(0), x)), ABS(APP(IVAR(0), y)), {x: y}),
        (APP(x, y), APP(IVAR(0), IVAR(1)), {x: IVAR(0), y: IVAR(1)}),
        (APP(x, x), APP(IVAR(0), IVAR(0)), {x: IVAR(0)}),
        (APP(x, x), APP(IVAR(0), IVAR(1)), None),
        (JOIN(x, y), JOIN(IVAR(0), IVAR(1)), {x: IVAR(0), y: IVAR(1)}),
        (JOIN(x, x), JOIN(IVAR(0), IVAR(0)), {x: IVAR(0)}),
        (JOIN(x, x), JOIN(IVAR(0), IVAR(1)), None),
        (QUOTE(x), QUOTE(y), {x: y}),
        (QUOTE(x), APP(x, y), None),
    ]
)
def test_match(pattern, term, expected):
    assert match(pattern, term) == expected
