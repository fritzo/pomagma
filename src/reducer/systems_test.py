from pomagma.reducer.syntax import ABS, APP, BOT, IVAR, JOIN, NVAR, TOP
from pomagma.reducer.systems import System, try_compute_step, try_decide_equal, unfold
from pomagma.util.testing import for_each

x = NVAR("x")
y = NVAR("y")
z = NVAR("z")
i0 = IVAR(0)


@for_each(
    [
        (System(x=y, y=y), x, y),
        (System(x=y, y=y), APP(x, x), APP(y, x)),
        (System(x=y, y=y), JOIN(x, y), y),
        (System(x=y, y=y, z=z), JOIN(x, JOIN(y, z)), JOIN(y, z)),
    ]
)
def test_unfold(system, body, expected):
    assert unfold(system, body) is expected


@for_each(
    [
        System(),
        System(x=ABS(i0)),
        System(x=ABS(APP(i0, TOP))),
        System(x=ABS(APP(i0, BOT))),
        System(x=ABS(i0), y=ABS(i0)),
    ]
)
def test_try_compute_step_normal(system):
    system = system.copy()
    assert not try_compute_step(system), system


@for_each(
    [
        (System(x=x), System(x=x)),
        (System(x=y, y=x), System(x=x, y=x)),
        (System(x=x, y=x), System(x=x, y=x)),
        (System(x=ABS(i0), y=APP(x, x)), System(x=ABS(i0), y=x)),
        (System(x=ABS(i0), y=x), System(x=ABS(i0), y=ABS(i0))),
    ]
)
def test_try_compute_step_nonnormal(system, expected):
    actual = system.copy()
    assert try_compute_step(actual)
    assert actual == expected


@for_each(
    [
        (System(x=ABS(i0), y=ABS(i0)), x, y, True),
        (System(x=ABS(i0), y=ABS(APP(i0, TOP))), x, y, False),
    ]
)
def test_try_decide_equal(system, lhs, rhs, expected):
    assert try_decide_equal(system, lhs, rhs) is expected
