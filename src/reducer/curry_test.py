from pomagma.reducer.curry import abstract, convert
from pomagma.reducer.syntax import (APP, BOT, IVAR, JOIN, NVAR, QUOTE, TOP, B,
                                    C, I, K, S, sexpr_parse)
from pomagma.util.testing import for_each

a = NVAR('a')
b = NVAR('b')
c = NVAR('c')
w = NVAR('w')
x = NVAR('x')
y = NVAR('y')
z = NVAR('z')
i0 = IVAR(0)
i1 = IVAR(1)


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


@for_each([
    ('TOP', 'TOP'),
    ('BOT', 'BOT'),
    ('(FUN x x)', 'I'),
    ('(FUN x TOP)', 'TOP'),
    ('(FUN x BOT)', 'BOT'),
    ('(FUN x (FUN y x))', 'K'),
    ('(FUN x (FUN y (FUN z (x (y z)))))', 'B'),
    ('(FUN x (FUN y (FUN z (x z y))))', 'C'),
    ('(FUN x (FUN y (FUN z (x z (y z)))))', 'S'),
])
def test_convert(code, expected):
    code = sexpr_parse(code)
    expected = sexpr_parse(expected)
    assert convert(code) is expected
