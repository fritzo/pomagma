from pomagma.reducer.code import TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import NVAR, APP, JOIN, QUOTE, FUN
from pomagma.reducer.code import polish_print
from pomagma.reducer.curry import compile_, decompile
from pomagma.reducer.curry import fresh_var, abstract, define, substitute
from pomagma.util.testing import for_each
import pytest

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
    (x, y, APP(y, z), APP(y, z)),
    (x, y, APP(x, z), APP(y, z)),
    (x, y, APP(z, x), APP(z, y)),
    (x, y, APP(x, x), APP(APP(APP(S, I), I), y)),
    (x, y, JOIN(y, z), JOIN(y, z)),
    (x, y, JOIN(x, z), JOIN(y, z)),
    (x, y, JOIN(z, x), JOIN(z, y)),
    (x, y, JOIN(x, x), APP(JOIN(I, I), y)),
    (x, y, QUOTE(y), QUOTE(y)),
    (x, y, QUOTE(z), QUOTE(z)),
    (x, y, QUOTE(x), QUOTE(y)),
    pytest.mark.xfail(
        (x, y, APP(x, QUOTE(x)), APP(y, QUOTE(y))),
        reason='too lazy around QUOTE',
    ),
])
def test_define(var, defn, body, expected):
    actual = define(var, defn, body)
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


a = fresh_var(0)
b = fresh_var(1)
c = fresh_var(2)


@for_each([
    (TOP, TOP),
    (APP(TOP, x), TOP),
    (BOT, BOT),
    (APP(BOT, x), BOT),
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
        APP(APP(FUN(a, APP(APP(x, a), APP(y, a))), FUN(b, b)), w),
    ),
    (JOIN(x, y), JOIN(x, y)),
])
def test_decompile(code, expected):
    actual_str = polish_print(decompile(code))
    expected_str = polish_print(expected)
    assert expected_str == actual_str


@for_each([
    TOP,
    BOT,
    I,
    K,
    B,
    C,
    S,
    APP(K, I),
    APP(C, I),
    APP(APP(C, I), I),
    APP(APP(S, I), I),
    JOIN(K, APP(K, I)),
    QUOTE(TOP),
    QUOTE(APP(C, I)),
])
def test_decompile_compile(code):
    expected_str = polish_print(code)
    decompiled = decompile(code)
    actual = compile_(decompiled)
    actual_str = polish_print(actual)
    assert actual_str == expected_str