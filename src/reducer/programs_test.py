import pytest

from pomagma.reducer import bohm, lib
from pomagma.reducer.programs import program, using_engine
from pomagma.reducer.sugar import app
from pomagma.util.testing import for_each

bool_not = program("bool", "bool")(lib.bool_not)
succ = program("num", "num")(lib.succ)
num_pred = program("num", "num")(lib.num_pred)


@program("num", "num")
def partial_pred(x):
    return app(x, lib.undefined, lambda px: px)


num_add = program("num", "num", "num")(lib.num_add)
num_lt = program("num", "num", "bool")(lib.num_lt)

CALL_EXAMPLES = [
    (bool_not, (True,), False),
    (bool_not, (False,), True),
    (bool_not, (0,), TypeError),
    (bool_not, ([],), TypeError),
    (succ, (0,), 1),
    (succ, (1,), 2),
    (succ, (2,), 3),
    (succ, (False,), TypeError),
    (succ, ([],), TypeError),
    (num_pred, (0,), RuntimeError),
    (num_pred, (1,), 0),
    (num_pred, (2,), 1),
    (num_pred, (True,), TypeError),
    (num_pred, ([],), TypeError),
    (partial_pred, (0,), NotImplementedError),
    (partial_pred, (1,), 0),
    (partial_pred, (2,), 1),
    (num_add, (0, 0), 0),
    (num_add, (0, 1), 1),
    (num_add, (0, 2), 2),
    (num_add, (1, 0), 1),
    (num_add, (1, 1), 2),
    (num_add, (1, 2), 3),
    (num_add, (2, 0), 2),
    (num_add, (2, 1), 3),
    (num_add, (2, 2), 4),
    (num_lt, (0, 0), False),
    (num_lt, (0, 1), True),
    (num_lt, (0, 2), True),
    (num_lt, (1, 0), False),
    (num_lt, (1, 1), False),
    (num_lt, (1, 2), True),
    (num_lt, (2, 0), False),
    (num_lt, (2, 1), False),
    (num_lt, (2, 2), False),
]


@for_each(CALL_EXAMPLES)
def test_call(fun, args, expected):
    with using_engine(bohm):
        if isinstance(expected, type) and issubclass(expected, Exception):
            with pytest.raises(expected):
                fun(*args)
        else:
            actual = fun(*args)
            assert actual == expected
