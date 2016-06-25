from pomagma.reducer.code import I, K, B, C, S
from pomagma.reducer.code import VAR, APP, JOIN, FUN, LET
from pomagma.reducer.code import serialize
from pomagma.reducer.transforms import abstract, decompile, fresh_var
from pomagma.util.testing import for_each

w = VAR('w')
x = VAR('x')
y = VAR('y')
z = VAR('z')


@for_each([
    (x, x, I),
    (x, y, APP(K, y)),
    (x, I, APP(K, I)),
    (x, APP(x, x), APP(APP(S, I), I)),
    (x, APP(x, y), APP(APP(C, I), y)),
    (x, APP(y, x), y),
    (x, APP(y, APP(z, x)), APP(APP(B, y), z)),
    (x, JOIN(x, x), JOIN(I, I)),
    (x, JOIN(x, y), JOIN(I, APP(K, y))),
    (x, JOIN(y, x), JOIN(APP(K, y), I)),
    (x, JOIN(y, z), APP(K, JOIN(y, z))),
])
def test_abstract(var, body, expected_abs):
    actual_abs = abstract(var, body)
    assert actual_abs == expected_abs


a = fresh_var(0)
b = fresh_var(1)
c = fresh_var(2)


@for_each([
    (I, FUN(a, a)),
    (APP(I, x), x),
    (APP(APP(I, x), y), APP(x, y)),
    (K, FUN(a, FUN(b, a))),
    (APP(K, x), FUN(a, x)),
    (APP(APP(K, x), y), x),
    (APP(APP(APP(K, x), y), z), APP(x, z)),
    (B, FUN(a, FUN(b, FUN(c, APP(a, APP(b, c)))))),
    (APP(B, x), FUN(a, FUN(b, APP(x, APP(a, b))))),
    (APP(APP(B, x), y), FUN(a, APP(x, APP(y, a)))),
    (APP(APP(APP(B, x), y), z), APP(x, APP(y, z))),
    (APP(APP(APP(APP(B, x), y), z), w), APP(APP(x, APP(y, z)), w)),
    (C, FUN(a, FUN(b, FUN(c, APP(APP(a, c), b))))),
    (APP(C, x), FUN(a, FUN(b, APP(APP(x, b), a)))),
    (APP(APP(C, x), y), FUN(a, APP(APP(x, a), y))),
    (APP(APP(APP(C, x), y), z), APP(APP(x, z), y)),
    (APP(APP(APP(APP(C, x), y), z), w), APP(APP(APP(x, z), y), w)),
    (S, FUN(a, FUN(b, FUN(c, APP(APP(a, c), APP(b, c)))))),
    (APP(S, x), FUN(a, FUN(b, APP(APP(x, b), APP(a, b))))),
    (APP(APP(S, x), y), FUN(a, APP(APP(x, a), APP(y, a)))),
    (APP(APP(APP(S, x), y), z), APP(APP(x, z), APP(y, z))),
    (APP(APP(APP(APP(S, x), y), z), w), APP(APP(APP(x, z), APP(y, z)), w)),
    (
        APP(APP(APP(APP(S, x), y), I), w),
        APP(LET(a, FUN(b, b), APP(APP(x, a), APP(y, a))), w),
    ),
])
def test_decompile(code, expected):
    actual_str = serialize(decompile(code))
    expected_str = serialize(expected)
    assert expected_str == actual_str
