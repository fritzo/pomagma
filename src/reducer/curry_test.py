from pomagma.reducer.curry import abstract
from pomagma.reducer.syntax import (APP, BOT, JOIN, NVAR, QUOTE, TOP, B, C, I,
                                    K, S)
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
    (x, QUOTE(y), APP(K, QUOTE(y))),
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
