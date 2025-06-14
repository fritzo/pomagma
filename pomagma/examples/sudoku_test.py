import pytest

from pomagma.examples import sudoku
from pomagma.reducer import bohm
from pomagma.reducer.programs import using_engine
from pomagma.util.testing import for_each

ALL_DIFFERENT_EXAMPLES = [
    (True, []),
    (True, [1]),
    (True, [1, 2]),
    (True, [2, 1]),
    (True, [1, 2, 3]),
    (True, [1, 3, 2]),
    (True, [2, 1, 3]),
    (True, [2, 3, 1]),
    (True, [3, 1, 2]),
    (True, [3, 2, 1]),
    (True, [1, 2, 3, 4, 5, 6, 7, 8, 9]),
    (False, [1, 1]),
    (False, [2, 2]),
    (False, [1, 2, 1]),
    (False, [3, 2, 3]),
    (False, [1, 2, 3, 2, 5]),
]


@for_each(ALL_DIFFERENT_EXAMPLES)
def test_all_different(expected, xs):
    assert sudoku.all_different(xs) == expected


@pytest.mark.xfail
@for_each(ALL_DIFFERENT_EXAMPLES)
def test_py_all_different(expected, xs):
    with using_engine(bohm):
        actual = sudoku.py_all_different(xs)
    assert actual == expected
