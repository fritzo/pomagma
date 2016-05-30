from pomagma.reducer import engine
from pomagma.reducer import io
from pomagma.reducer.code import TOP, BOT
from pomagma.reducer.programs import program
from pomagma.reducer.programs import using_engine
from pomagma.reducer.sugar import app, rec
from pomagma.util import TODO
import pytest


@program('bool', 'bool')
def neg(x):
    return app(x, io.false, io.true)


@program('num', 'num')
def succ(n):
    return io.succ(n)


@program('num', 'num')
def pred(n):
    return app(n, TOP, lambda px: px)


@program('num', 'num')
def partial_pred(x):
    return app(x, BOT, lambda px: px)


@program('num', 'num', 'num')
def add(x, y):
    add = rec(lambda add, x:
              app(x, lambda y: y, lambda px, y: io.succ(app(add, px, y))))
    return app(add, x, y)


@program('num', 'num', 'bool')
def num_less(x, y):
    less = rec(lambda less, x, y:
               app(y, io.false, lambda py:
                   app(x, io.true, lambda px: app(less, px, py))))
    return app(less, x, y)


@program(('list', 'num'), ('list', 'num'))
def list_num_sort(xs):
    TODO('implicit sort')


EXAMPLES = [
    (neg, (True,), False),
    (neg, (False,), True),
    (neg, (0,), TypeError),
    (neg, ([],), TypeError),
    (succ, (0,), 1),
    (succ, (1,), 2),
    (succ, (2,), 3),
    (succ, (False,), TypeError),
    (succ, ([],), TypeError),
    (pred, (0,), RuntimeError),
    (pred, (1,), 0),
    (pred, (2,), 1),
    (pred, (True,), TypeError),
    (pred, ([],), TypeError),
    (partial_pred, (0,), NotImplementedError),
    (partial_pred, (1,), 0),
    (partial_pred, (2,), 1),
    pytest.mark.xfail((add, (0, 0), 0)),
    pytest.mark.xfail((add, (0, 1), 1)),
    pytest.mark.xfail((add, (0, 2), 2)),
    pytest.mark.xfail((add, (1, 0), 1)),
    pytest.mark.xfail((add, (1, 1), 2)),
    pytest.mark.xfail((add, (1, 2), 3)),
    pytest.mark.xfail((add, (2, 0), 2)),
    pytest.mark.xfail((add, (2, 1), 3)),
    pytest.mark.xfail((add, (2, 2), 4)),
    pytest.mark.xfail((num_less, (0, 0), False)),
    pytest.mark.xfail((num_less, (0, 1), True)),
    pytest.mark.xfail((num_less, (0, 2), True)),
    pytest.mark.xfail((num_less, (1, 0), False)),
    pytest.mark.xfail((num_less, (1, 1), False)),
    pytest.mark.xfail((num_less, (1, 2), True)),
    pytest.mark.xfail((num_less, (2, 0), False)),
    pytest.mark.xfail((num_less, (2, 1), False)),
    pytest.mark.xfail((num_less, (2, 2), False)),
]


@pytest.mark.parametrize('fun,args,expected', EXAMPLES)
def test_call(fun, args, expected):
    with using_engine(engine):
        if isinstance(expected, type) and issubclass(expected, Exception):
            with pytest.raises(expected):
                fun(*args)
        else:
            actual = fun(*args)
            assert actual == expected
