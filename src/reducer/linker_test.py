from pomagma.reducer import lib
from pomagma.reducer.code import VAR, S
from pomagma.reducer.linker import link
from pomagma.reducer.sugar import as_code, app
from pomagma.util.testing import for_each

x = VAR('x')


@for_each([
    (VAR('lib.true'), lib.true),
    (VAR('lib.false'), lib.false),
    (VAR('lib.zero'), lib.zero),
    (VAR('lib.succ'), lib.succ),
    (app(x, VAR('lib.ok'), VAR('lib.ok')), app(S, x, lib.ok, lib.ok)),
])
def test_link(code, expected):
    expected = as_code(expected)
    actual = link(code)
    assert actual == expected
