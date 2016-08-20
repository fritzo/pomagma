from pomagma.reducer import lib
from pomagma.reducer.code import NVAR, S
from pomagma.reducer.linker import link
from pomagma.reducer.sugar import as_code, app
from pomagma.util.testing import for_each

x = NVAR('x')


@for_each([
    (NVAR('lib.true'), lib.true),
    (NVAR('lib.false'), lib.false),
    (NVAR('lib.zero'), lib.zero),
    (NVAR('lib.succ'), lib.succ),
    (app(x, NVAR('lib.ok'), NVAR('lib.ok')), app(S, x, lib.ok, lib.ok)),
])
def test_link(code, expected):
    expected = as_code(expected)
    actual = link(code)
    assert actual == expected
