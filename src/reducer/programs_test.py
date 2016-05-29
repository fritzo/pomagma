from pomagma.reducer import io
from pomagma.reducer.programs import program
from pomagma.reducer.programs import using_engine
from pomagma.reducer.sugar import app, rec
from pomagma.util import TODO
import pytest


@program('num', 'num')
def succ(n):
    return io.succ(n)


@program('num', 'num', 'num')
def add(x, y):
    return rec(lambda add: app(x, y, lambda px: io.succ(app(add, px, y))))


@program('num', 'num', 'bool')
def num_less(num_less, x, y):
    return rec(lambda num_less:
               app(y, io.false, lambda py:
                   app(x, io.true, lambda px: app(num_less, px, py))))


@program(('list', 'num'), ('list', 'num'))
def list_num_sort(xs):
    TODO('implicit sort')


EXAMPLES = [
    (succ, (0,), 1),
    (succ, (1,), 2),
    (succ, (2,), 3),
    (add, (0, 0), 0),
    (add, (0, 1), 1),
    (add, (0, 2), 2),
    (add, (1, 0), 1),
    (add, (1, 1), 2),
    (add, (1, 2), 3),
    (add, (2, 0), 2),
    (add, (2, 1), 3),
    (add, (2, 2), 4),
    (num_less, (0, 0), False),
    (num_less, (0, 1), True),
    (num_less, (0, 2), True),
    (num_less, (1, 0), False),
    (num_less, (1, 1), False),
    (num_less, (1, 2), True),
    (num_less, (2, 0), False),
    (num_less, (2, 1), False),
    (num_less, (2, 2), False),
]


@pytest.mark.xfail(reason='TODO implement an engine')
@pytest.mark.parametrize('fun,args,expected_result', EXAMPLES)
def test_call(fun, args, expected_result):
    with using_engine(TODO('impelement an engine')):
        actual_result = fun(*args)
    assert actual_result == expected_result
