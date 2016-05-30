from pomagma.examples import sudoku
from pomagma.reducer import engine
from pomagma.reducer.programs import using_engine
import pytest

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


@pytest.mark.parametrize('expected,xs', ALL_DIFFERENT_EXAMPLES)
def test_all_different(expected, xs):
    assert sudoku.all_different(xs) == expected


@pytest.mark.xfail
@pytest.mark.parametrize('expected,xs', ALL_DIFFERENT_EXAMPLES)
def test_py_all_different(expected, xs):
    with using_engine(engine):
        actual = sudoku.py_all_different(xs)
    assert actual == expected
