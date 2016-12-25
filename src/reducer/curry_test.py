from pomagma.reducer.syntax import TOP, BOT, I, K, B, C, S
from pomagma.reducer.syntax import NVAR, APP, JOIN, QUOTE
from pomagma.reducer.curry import abstract, substitute
from pomagma.util.testing import for_each

a = NVAR('a')
b = NVAR('b')
c = NVAR('c')
w = NVAR('w')
x = NVAR('x')
y = NVAR('y')
z = NVAR('z')


@for_each([
    (x, x, I),
    (x, y, APP(K, y)),
    (x, TOP, TOP),
    (x, BOT, BOT),
    (x, I, APP(K, I)),
    (x, APP(x, x), APP(APP(S, I), I)),
    (x, APP(x, y), APP(APP(C, I), y)),
    (x, APP(y, x), y),
    (x, APP(y, APP(z, x)), APP(APP(B, y), z)),
    (x, JOIN(x, x), JOIN(I, I)),
    (x, JOIN(x, y), JOIN(I, APP(K, y))),
    (x, JOIN(y, x), JOIN(APP(K, y), I)),
    (x, JOIN(y, z), APP(K, JOIN(y, z))),
    (x, JOIN(APP(y, x), APP(z, x)), JOIN(y, z)),
])
def test_abstract(var, body, expected):
    actual = abstract(var, body)
    assert actual == expected


@for_each([
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
])
def test_substitute(var, defn, body, expected):
    actual = substitute(var, defn, body)
    assert actual == expected
