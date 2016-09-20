from pomagma.reducer.util import trool_all, trool_any
from pomagma.util.testing import for_each


@for_each([
    (True, []),
    (True, [True]),
    (None, [None]),
    (False, [False]),
    (True, [True, True]),
    (None, [True, None]),
    (False, [True, False]),
    (None, [None, True]),
    (False, [None, False]),
    (None, [None, None]),
    (False, [False, True]),
    (False, [False, None]),
    (False, [False, False]),
])
def test_trool_all(expected, values):
    assert trool_all(values) == expected


@for_each([
    (False, []),
    (True, [True]),
    (None, [None]),
    (False, [False]),
    (True, [True, True]),
    (True, [True, None]),
    (True, [True, False]),
    (True, [None, True]),
    (None, [None, False]),
    (None, [None, None]),
    (True, [False, True]),
    (None, [False, None]),
    (False, [False, False]),
])
def test_trool_any(expected, values):
    assert trool_any(values) == expected
