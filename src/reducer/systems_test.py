from pomagma.reducer.syntax import ABS, APP, BOT, IVAR, NVAR, TOP
from pomagma.reducer.systems import System, try_beta_step, unfold
from pomagma.util.testing import for_each

x = NVAR('x')
y = NVAR('y')
z = NVAR('z')
i0 = IVAR(0)


@for_each([
    (System(), True),
    (System(x=x), True),
    (System(x=y), False),
])
def test_is_closed(system, expected):
    assert system.is_closed() is expected


@for_each([
    (System(x=y), x, y),
    (System(x=y), APP(x, x), APP(y, x)),
])
def test_unfold(system, body, expected):
    assert unfold(system, body) is expected


@for_each([
    System(),
    System(x=ABS(i0)),
    System(x=ABS(APP(i0, TOP))),
    System(x=ABS(APP(i0, BOT))),
    System(x=ABS(i0), y=ABS(i0)),
])
def test_try_beta_step_normal(system):
    system = system.copy()
    assert not try_beta_step(system), system


@for_each([
    (System(x=x), System(x=x)),
    (System(x=y, y=x), System(x=x, y=x)),
    (System(x=x, y=x), System(x=x, y=x)),
    (System(x=ABS(i0), y=APP(x, x)), System(x=ABS(i0), y=x)),
    (System(x=ABS(i0), y=x), System(x=ABS(i0), y=ABS(i0))),
])
def test_try_beta_step_nonnormal(system, expected):
    actual = system.copy()
    assert try_beta_step(actual)
    assert actual == expected
