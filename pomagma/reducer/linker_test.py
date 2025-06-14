from pomagma.reducer import lib
from pomagma.reducer.linker import link, substitute
from pomagma.reducer.sugar import app, as_term
from pomagma.reducer.syntax import ABS, APP, IVAR, JOIN, NVAR, QUOTE, I
from pomagma.util.testing import for_each

x = NVAR("x")
y = NVAR("y")
z = NVAR("z")


@for_each(
    [
        (x, y, z, z),
        (x, y, y, y),
        (x, y, x, y),
        (x, y, I, I),
        (x, y, APP(x, z), APP(y, z)),
        (x, y, APP(z, x), APP(z, y)),
        (x, y, APP(x, x), APP(y, y)),
        (x, y, JOIN(x, z), JOIN(y, z)),
        (x, y, JOIN(z, x), JOIN(z, y)),
        (x, y, JOIN(x, x), JOIN(y, y)),
        (x, y, QUOTE(y), QUOTE(y)),
        (x, y, QUOTE(z), QUOTE(z)),
        (x, y, QUOTE(x), QUOTE(y)),
        (x, y, APP(x, QUOTE(x)), APP(y, QUOTE(y))),
        (x, ABS(IVAR(0)), ABS(x), ABS(ABS(IVAR(0)))),
        (x, ABS(IVAR(0)), ABS(APP(x, IVAR(0))), ABS(APP(ABS(IVAR(0)), IVAR(0)))),
    ]
)
def test_substitute(var, defn, body, expected):
    actual = substitute(var, defn, body)
    assert actual == expected


@for_each(
    [
        (NVAR("lib.true"), lib.true),
        (NVAR("lib.false"), lib.false),
        (NVAR("lib.zero"), lib.zero),
        (NVAR("lib.succ"), lib.succ),
        (app(x, NVAR("lib.ok"), NVAR("lib.ok")), app(x, lib.ok, lib.ok)),
    ]
)
def test_link(term, expected):
    expected = as_term(expected)
    actual = link(term)
    assert actual == expected
