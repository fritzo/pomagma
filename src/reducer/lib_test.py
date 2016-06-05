from pomagma.reducer import lib
from pomagma.reducer.code import VAR
from pomagma.reducer.engine import simplify
from pomagma.reducer.sugar import as_code, app
from pomagma.util import TRAVIS_CI
from pomagma.util.testing import for_each
import pytest

f = VAR('f')
x = VAR('x')
y = VAR('y')

ok = lib.ok
error = lib.error
undefined = lib.undefined
true = lib.true
false = lib.false


@for_each([
    ('ok', lambda x: x),
    ('true', lambda x, y: x),
    ('false', lambda x, y: y),
    ('none', lambda f, g: f),
    ('some', lambda x, f, g: app(g, x)),
    ('pair', lambda x, y, f: app(f, x, y)),
    ('inl', lambda x, f, g: app(f, x)),
    ('inr', lambda y, f, g: app(g, y)),
    ('zero', lambda z, s: z),
    ('succ', lambda n, z, s: app(s, n)),
    ('nil', lambda n, c: n),
    ('cons', lambda head, tail, n, c: app(c, head, tail)),
])
def test_intro_forms(name, native):
    assert as_code(getattr(lib, name)) == as_code(native)


# ----------------------------------------------------------------------------
# Unit

@for_each([
    (ok, ok),
    (error, error),
    (undefined, undefined),
])
def test_unit_test(x, expected):
    assert simplify(lib.unit_test(x)) == expected


@for_each([
    (ok, ok, ok),
    (ok, undefined, undefined),
    (undefined, ok, undefined),
    (undefined, undefined, undefined),
])
def test_unit_and(x, y, expected):
    assert simplify(lib.unit_and(x, y)) == expected


@for_each([
    (ok, ok, ok),
    (ok, undefined, ok),
    (undefined, ok, ok),
    (undefined, undefined, undefined),
])
def test_unit_or(x, y, expected):
    assert simplify(lib.unit_or(x, y)) == expected


# ----------------------------------------------------------------------------
# Bool

@for_each([
    (true, ok),
    (false, ok),
    (error, error),
    (undefined, undefined),
])
def test_bool_test(x, expected):
    assert simplify(lib.bool_test(x)) == expected


@for_each([
    (true, false),
    (false, true),
    (undefined, undefined),
    (error, error),
])
def test_bool_not(x, expected):
    assert simplify(lib.bool_not(x)) == expected


@for_each([
    (true, true, true),
    (true, false, false),
    (true, undefined, undefined),
    (false, true, false),
    (false, false, false),
    (false, undefined, false),
    (undefined, true, undefined),
    (undefined, undefined, undefined),
    pytest.mark.xfail((undefined, false, false)),
    (error, x, error),
    pytest.mark.xfail((x, error, error)),
])
def test_bool_and(x, y, expected):
    assert simplify(lib.bool_and(x, y)) == expected


@for_each([
    (true, true, true),
    (true, false, true),
    (true, undefined, true),
    (false, true, true),
    (false, false, false),
    (false, undefined, undefined),
    (undefined, false, undefined),
    (undefined, undefined, undefined),
    (error, x, error),
    pytest.mark.xfail((x, error, error)),
])
def test_bool_or(x, y, expected):
    assert simplify(lib.bool_or(x, y)) == expected


# ----------------------------------------------------------------------------
# Maybe

@for_each([
    (lib.none, ok),
    (lib.some(x), ok),
    (error, error),
    (undefined, undefined),
])
def test_maybe_test(x, expected):
    assert simplify(lib.maybe_test(x)) == expected


# ----------------------------------------------------------------------------
# Products

xy = lib.pair(x, y)


@for_each([
    (xy, ok),
    (error, error),
    (undefined, undefined),
])
def test_prod_test(x, expected):
    assert simplify(lib.prod_test(x)) == expected


@for_each([
    (xy, x),
    (error, error),
    (undefined, undefined),
])
def test_prod_fst(x, expected):
    assert simplify(lib.prod_fst(x)) == expected


@for_each([
    (xy, y),
    (error, error),
    (undefined, undefined),
])
def test_prod_snd(x, expected):
    assert simplify(lib.prod_snd(x)) == expected


# ----------------------------------------------------------------------------
# Sums

@for_each([
    (lib.inl(x), ok),
    (lib.inr(y), ok),
    (error, error),
    (undefined, undefined),
])
def test_sum_test(x, expected):
    assert simplify(lib.sum_test(x)) == expected


# ----------------------------------------------------------------------------
# Numerals as Y Maybe

succ = lib.succ
zero = lib.zero
one = succ(zero)
two = succ(one)
three = succ(two)


@for_each([
    (zero, ok),
    (one, ok),
    pytest.mark.xfail((two, ok)),
    pytest.mark.xfail((three, ok)),
    (error, error),
    (succ(error), error),
    (succ(succ(error)), error),
    pytest.mark.xfail((succ(succ(succ(error))), error)),
    (undefined, undefined),
    (succ(undefined), undefined),
    (succ(succ(undefined)), undefined),
    pytest.mark.xfail((succ(succ(succ(undefined))), undefined)),
])
def test_num_test(x, expected):
    assert simplify(lib.num_test(x)) == expected


@for_each([
    (zero, true),
    (one, false),
    (two, false),
    (three, false),
    (undefined, undefined),
    (error, error),
])
def test_num_is_zero(x, expected):
    assert simplify(lib.num_is_zero(x)) == expected


@for_each([
    (zero, error),
    (one, zero),
    (two, one),
    (three, two),
    (undefined, undefined),
    (succ(undefined), undefined),
    (error, error),
    (succ(error), error),
])
def test_num_pred(x, expected):
    assert simplify(lib.num_pred(x)) == expected


@for_each([
    (zero, zero, zero),
    pytest.mark.xfail((zero, two, two)),
    pytest.mark.xfail((zero, three, three)),
    pytest.mark.xfail((zero, one, one)),
    (one, zero, one),
    pytest.mark.xfail((one, one, two)),
    pytest.mark.xfail((one, two, three)),
    (two, zero, two),
    pytest.mark.xfail((two, one, three)),
    (three, zero, three),
    (undefined, zero, undefined),
    (zero, undefined, undefined),
    pytest.mark.xfail((error, x, error)),
    (x, error, error),
])
def test_num_add(x, y, expected):
    assert simplify(lib.num_add(x, y)) == expected


@for_each([
    (zero, zero, true),
    (zero, one, false),
    (zero, two, false),
    (one, zero, false),
    (one, one, true),
    (one, two, false),
    (two, zero, false),
    (two, one, false),
    pytest.mark.xfail((two, two, true)),
])
def test_num_eq(x, y, expected):
    assert simplify(lib.num_eq(x, y)) == expected


@for_each([
    (zero, zero, false),
    (zero, one, true),
    (zero, two, true),
    (one, zero, false),
    (one, one, false),
    (one, two, true),
    (two, zero, false),
    (two, one, false),
    pytest.mark.xfail((two, two, false)),
])
def test_num_less(x, y, expected):
    assert simplify(lib.num_less(x, y)) == expected


@for_each([
    (zero, succ, zero, zero),
    pytest.mark.xfail((zero, succ, one, one)),
    pytest.mark.xfail((zero, succ, two, two)),
    pytest.mark.xfail((zero, succ, three, three)),
    (one, succ, zero, one),
    pytest.mark.xfail((one, succ, one, two)),
    pytest.mark.xfail((one, succ, two, three)),
    pytest.mark.xfail((zero, lambda x: succ(succ(x)), zero, two)),
    pytest.mark.xfail((one, lambda x: succ(succ(x)), zero, three)),
    pytest.mark.xfail((one, lambda x: succ(succ(x)), zero, three)),
    (true, lambda x: false, zero, true),
    (true, lambda x: false, one, false),
    (true, lambda x: false, two, false),
    (y, ok, zero, y),
    (y, ok, one, y),
    pytest.mark.xfail((y, ok, two, y)),
    pytest.mark.xfail((y, ok, three, y)),
    (y, ok, undefined, undefined),
    (y, ok, error, error),
])
def test_num_rec(z, s, x, expected):
    assert simplify(lib.num_rec(z, s, x)) == expected


# ----------------------------------------------------------------------------
# Finite homogeneous lists

nil = lib.nil
cons = lib.cons


@for_each([
    (nil, ok),
    (cons(x, nil), ok),
    (error, error),
    (undefined, undefined),
    (cons(x, error), error),
    (cons(x, undefined), undefined),
])
def test_list_test(x, expected):
    assert simplify(lib.list_test(x)) == expected


@for_each([
    (nil, true),
    (cons(x, nil), false),
    (undefined, undefined),
    (error, error),
])
def test_list_empty(x, expected):
    assert simplify(lib.list_empty(x)) == expected


@for_each([
    (nil, true),
    pytest.mark.skipif(TRAVIS_CI, reason='wtf')((cons(true, nil), true)),
    (cons(false, nil), false),
    pytest.mark.xfail((cons(true, cons(true, nil)), true)),
    pytest.mark.skipif(TRAVIS_CI, reason='wtf')(
        (cons(true, cons(false, nil)), false)),
    (cons(false, cons(true, nil)), false),
    (cons(false, cons(false, nil)), false),
])
def test_list_all(x, expected):
    assert simplify(lib.list_all(x)) == expected


@for_each([
    (nil, false),
    (cons(true, nil), true),
    (cons(false, nil), false),
    (cons(true, cons(true, nil)), true),
    (cons(true, cons(false, nil)), true),
    (cons(false, cons(true, nil)), true),
    (cons(false, cons(false, nil)), false),
])
def test_list_any(x, expected):
    assert simplify(lib.list_any(x)) == expected


@for_each([
    (lambda x: x, nil, nil),
    (undefined, nil, nil),
    (error, nil, nil),
    (lambda x: x, cons(x, nil), cons(x, nil)),
    (lib.bool_not, cons(false, nil), cons(true, nil)),
    (lib.bool_not, cons(true, nil), cons(false, nil)),
    pytest.mark.xfail((
        lib.bool_not,
        cons(true, cons(false, nil)),
        cons(false, cons(true, nil)),
    )),
])
def test_list_map(f, x, expected):
    assert simplify(lib.list_map(f, x)) == expected


@for_each([
    (nil, cons, nil, nil),
    (nil, undefined, nil, nil),
    (nil, error, nil, nil),
    pytest.mark.xfail((nil, cons, cons(x, nil), cons(x, nil))),
    pytest.mark.xfail((nil, cons, cons(x, undefined), cons(x, undefined))),
    pytest.mark.xfail((nil, cons, cons(x, error), cons(x, error))),
])
def test_list_rec(n, c, x, expected):
    assert simplify(lib.list_rec(n, c, x)) == expected
