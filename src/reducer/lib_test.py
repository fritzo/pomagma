from pomagma.reducer import lib
from pomagma.reducer.code import VAR, I, J, UNIT
from pomagma.reducer.engine import reduce, simplify
from pomagma.reducer.engine_test import s_quoted
from pomagma.reducer.sugar import as_code, app, quote
from pomagma.util import TRAVIS_CI
from pomagma.util.testing import for_each
import hypothesis
import pytest

f = VAR('f')
x = VAR('x')
y = VAR('y')
z = VAR('z')

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
    (true, error),
    (false, error),
    (J, error),
    (x, app(UNIT, x)),
])
def test_unit_type(x, expected):
    assert simplify(lib.unit_type(x)) == expected


@for_each([
    (ok, ok),
    (error, error),
    (undefined, undefined),
    (true, error),
    (false, error),
    (x, app(UNIT, x)),
])
def test_unit_test(x, expected):
    assert simplify(lib.unit_test(x)) == expected


@for_each([
    (ok, ok, ok),
    (ok, undefined, undefined),
    (undefined, ok, undefined),
    (undefined, undefined, undefined),
    (ok, true, error),
    (ok, false, error),
    (true, ok, error),
    (false, ok, error),
])
def test_unit_and(x, y, expected):
    assert simplify(lib.unit_and(x, y)) == expected


@for_each([
    (ok, ok, ok),
    (ok, undefined, ok),
    (undefined, ok, ok),
    (undefined, undefined, undefined),
    (ok, true, error),
    (ok, false, error),
    (true, ok, error),
    (false, ok, error),
])
def test_unit_or(x, y, expected):
    assert simplify(lib.unit_or(x, y)) == expected


@for_each([
    (ok, quote(ok)),
    (undefined, undefined),
    (error, error),
    (true, error),
    (false, error),
])
def test_unit_quote(x, expected):
    assert simplify(lib.unit_quote(x)) == expected


# ----------------------------------------------------------------------------
# Bool

@for_each([
    (true, true),
    (false, false),
    (error, error),
    (undefined, undefined),
    (ok, error),
    (J, error),
])
def test_bool_type(x, expected):
    assert simplify(lib.bool_type(x)) == expected


@for_each([
    (true, ok),
    (false, ok),
    (error, error),
    (undefined, undefined),
    (ok, error),
    (J, error),
])
def test_bool_test(x, expected):
    assert simplify(lib.bool_test(x)) == expected


@for_each([
    (true, false),
    (false, true),
    (undefined, undefined),
    (error, error),
    (ok, error),
    (J, error),
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
    (undefined, false, false),
    (error, x, error),
    (x, error, error),
    (ok, true, error),
    (ok, false, error),
    (true, ok, error),
    (false, ok, error),
    (J, true, error),
    (J, false, error),
    (true, J, error),
    (false, J, error),
])
def test_bool_and(x, y, expected):
    assert reduce(lib.bool_and(x, y)) == expected


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
    (x, error, error),
    (ok, true, error),
    (ok, false, error),
    (true, ok, error),
    (false, ok, error),
    (J, true, error),
    (J, false, error),
    (true, J, error),
    (false, J, error),
])
def test_bool_or(x, y, expected):
    assert reduce(lib.bool_or(x, y)) == expected


@for_each([
    (true, quote(true)),
    (false, quote(false)),
    (undefined, undefined),
    (error, error),
    (ok, error),
    (J, error),
])
def test_bool_quote(x, expected):
    assert simplify(lib.bool_quote(x)) == expected


# ----------------------------------------------------------------------------
# Maybe

@for_each([
    (lib.none, lib.none),
    (lib.some(undefined), lib.some(undefined)),
    (lib.some(error), lib.some(error)),
    (lib.some(ok), lib.some(ok)),
    (lib.some(true), lib.some(true)),
    (lib.some(false), lib.some(false)),
    (error, error),
    (undefined, undefined),
    (ok, error),
    (J, error),
    (app(J, lib.none, lib.some(undefined)), error),
    pytest.mark.xfail((app(J, lib.some(true), lib.some(false)), lib.some(J))),
])
def test_maybe_type(x, expected):
    assert simplify(lib.maybe_type(x)) == expected


@for_each([
    (lib.none, ok),
    (lib.some(x), ok),
    (error, error),
    (undefined, undefined),
])
def test_maybe_test(x, expected):
    assert simplify(lib.maybe_test(x)) == expected


@for_each([
    (lib.none, quote(lib.none)),
    (lib.some(true), quote(lib.some(true))),
    (undefined, undefined),
    (error, error),
])
def test_maybe_quote(x, expected):
    quote_some = lib.bool_quote
    assert simplify(lib.maybe_quote(quote_some, x)) == expected


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


@for_each([
    (lib.pair(ok, false), quote(lib.pair(ok, false))),
    (undefined, undefined),
    (error, error),
])
def test_prod_quote(x, expected):
    quote_fst = lib.unit_quote
    quote_snd = lib.bool_quote
    assert simplify(lib.prod_quote(quote_fst, quote_snd, x)) == expected


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


@for_each([
    (lib.inl(ok), quote(lib.inl(ok))),
    (lib.inr(true), quote(lib.inr(true))),
    (lib.inr(false), quote(lib.inr(false))),
    (undefined, undefined),
    (error, error),
])
def test_sum_quote(x, expected):
    quote_inl = lib.unit_quote
    quote_inr = lib.bool_quote
    assert simplify(lib.sum_quote(quote_inl, quote_inr, x)) == expected


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
    (two, ok),
    (three, ok),
    (error, error),
    (succ(error), error),
    (succ(succ(error)), error),
    (succ(succ(succ(error))), error),
    (undefined, undefined),
    (succ(undefined), undefined),
    (succ(succ(undefined)), undefined),
    (succ(succ(succ(undefined))), undefined),
])
def test_num_test(x, expected):
    assert reduce(lib.num_test(x)) == expected


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
    (zero, two, two),
    (zero, three, three),
    (zero, one, one),
    (one, zero, one),
    (one, one, two),
    (one, two, three),
    (two, zero, two),
    (two, one, three),
    (three, zero, three),
    (undefined, zero, undefined),
    (zero, undefined, undefined),
    (error, x, error),
    (x, error, error),
])
def test_num_add(x, y, expected):
    assert reduce(lib.num_add(x, y)) == expected


@for_each([
    (zero, zero, true),
    (zero, one, false),
    (zero, two, false),
    (zero, three, false),
    (one, zero, false),
    (one, one, true),
    (one, two, false),
    (one, three, false),
    (two, zero, false),
    (two, one, false),
    (two, two, true),
    (two, three, false),
    (three, zero, false),
    (three, one, false),
    (three, two, false),
    (three, three, true),
])
def test_num_eq(x, y, expected):
    assert reduce(lib.num_eq(x, y)) == expected


@for_each([
    (zero, zero, false),
    (zero, one, true),
    (zero, two, true),
    (zero, three, true),
    (one, zero, false),
    (one, one, false),
    (one, two, true),
    (one, three, true),
    (two, zero, false),
    (two, one, false),
    (two, two, false),
    (two, three, true),
    (three, zero, false),
    (three, one, false),
    (three, two, false),
    (three, three, false),
])
def test_num_less(x, y, expected):
    assert reduce(lib.num_less(x, y)) == expected


@for_each([
    (zero, succ, zero, zero),
    (zero, succ, one, one),
    (zero, succ, two, two),
    (zero, succ, three, three),
    (one, succ, zero, one),
    (one, succ, one, two),
    (one, succ, two, three),
    (zero, lambda x: succ(succ(x)), zero, zero),
    (zero, lambda x: succ(succ(x)), one, two),
    (one, lambda x: succ(succ(x)), zero, one),
    (one, lambda x: succ(succ(x)), one, three),
    (true, lambda x: false, zero, true),
    (true, lambda x: false, one, false),
    (true, lambda x: false, two, false),
    (y, ok, zero, y),
    (y, ok, one, y),
    (y, ok, two, y),
    (y, ok, three, y),
    (y, ok, undefined, undefined),
    (y, ok, error, error),
])
def test_num_rec(z, s, x, expected):
    assert reduce(lib.num_rec(z, s, x)) == expected


@for_each([
    (zero, quote(zero)),
    (one, quote(one)),
    (two, quote(two)),
    (three, quote(three)),
    (undefined, undefined),
    (error, error),
])
def test_num_quote(x, expected):
    assert reduce(lib.num_quote(x)) == expected


# ----------------------------------------------------------------------------
# Finite homogeneous lists

nil = lib.nil
cons = lib.cons


@for_each([
    (nil, ok),
    (cons(x, nil), ok),
    (cons(x, cons(y, nil)), ok),
    (cons(x, cons(y, cons(z, nil))), ok),
    (error, error),
    (cons(x, error), error),
    (cons(x, cons(y, error)), error),
    (cons(x, cons(y, cons(z, error))), error),
    (undefined, undefined),
    (cons(x, undefined), undefined),
    (cons(x, cons(y, undefined)), undefined),
    (cons(x, cons(y, cons(z, undefined))), undefined),
])
def test_list_test(x, expected):
    assert reduce(lib.list_test(x)) == expected


@for_each([
    (nil, true),
    (cons(x, nil), false),
    (cons(x, cons(y, nil)), false),
    (cons(x, cons(y, cons(z, nil))), false),
    (cons(x, error), false),
    (cons(x, undefined), false),
    (error, error),
    (undefined, undefined),
])
def test_list_empty(x, expected):
    assert simplify(lib.list_empty(x)) == expected


@for_each([
    (nil, true),
    pytest.mark.skipif(TRAVIS_CI, reason='wtf')((cons(true, nil), true)),
    (cons(false, nil), false),
    pytest.mark.skipif(TRAVIS_CI, reason='wtf')(
        (cons(true, cons(true, nil)), true)),
    pytest.mark.skipif(TRAVIS_CI, reason='wtf')(
        (cons(true, cons(false, nil)), false)),
    (cons(false, cons(true, nil)), false),
    (cons(false, cons(false, nil)), false),
])
def test_list_all(x, expected):
    assert reduce(lib.list_all(x)) == expected


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
    assert reduce(lib.list_any(x)) == expected


@for_each([
    (lambda x: x, nil, nil),
    (undefined, nil, nil),
    (error, nil, nil),
    (lambda x: x, cons(x, nil), cons(x, nil)),
    (lib.bool_not, cons(false, nil), cons(true, nil)),
    (lib.bool_not, cons(true, nil), cons(false, nil)),
    (
        lib.bool_not,
        cons(true, cons(false, nil)),
        cons(false, cons(true, nil)),
    ),
    (
        lib.bool_not,
        cons(true, cons(true, cons(false, nil))),
        cons(false, cons(false, cons(true, nil))),
    ),
])
def test_list_map(f, x, expected):
    assert reduce(lib.list_map(f, x)) == expected


@for_each([
    (nil, cons, nil, nil),
    (nil, undefined, nil, nil),
    (nil, error, nil, nil),
    (nil, cons, cons(x, nil), cons(x, nil)),
    (nil, cons, cons(x, undefined), cons(x, undefined)),
    (nil, cons, cons(x, error), cons(x, error)),
])
def test_list_rec(n, c, x, expected):
    assert reduce(lib.list_rec(n, c, x)) == expected


@for_each([
    (nil, quote(nil)),
    pytest.mark.xfail((cons(zero, nil), quote(cons(zero, nil)))),
    pytest.mark.xfail((cons(one, nil), quote(cons(one, nil)))),
    pytest.mark.xfail((cons(two, nil), quote(cons(two, nil)))),
    pytest.mark.xfail((cons(three, nil), quote(cons(three, nil)))),
    pytest.mark.xfail(
        (cons(two, cons(zero, nil)), quote(cons(two, cons(zero, nil))))),
    (undefined, undefined),
    (error, error),
])
def test_list_quote(x, expected):
    quote_item = lib.num_quote
    assert reduce(lib.list_quote(quote_item, x)) == expected


# ----------------------------------------------------------------------------
# Functions

fun_t = lib.fun_type
unit_t = lib.unit_type
bool_t = lib.bool_type
maybe_t = lib.maybe_type


@for_each([
    (unit_t, fun_t(unit_t, unit_t)),
    (lib.unit_test, fun_t(unit_t, unit_t)),
    pytest.mark.xfail((lib.unit_and, fun_t(unit_t, fun_t(unit_t, unit_t)))),
    (lib.unit_or, fun_t(unit_t, fun_t(unit_t, unit_t))),
    (bool_t, fun_t(bool_t, bool_t)),
    (lib.bool_test, fun_t(bool_t, unit_t)),
    (lib.bool_not, fun_t(bool_t, bool_t)),
    pytest.mark.xfail((lib.bool_and, fun_t(bool_t, fun_t(bool_t, bool_t)))),
    pytest.mark.xfail((lib.bool_or, fun_t(bool_t, fun_t(bool_t, bool_t)))),
    (maybe_t, fun_t(maybe_t, maybe_t)),
    (lib.maybe_test, fun_t(maybe_t, unit_t)),
])
def test_fun_type_fixes(value, type_):
    assert reduce(app(type_, value)) == reduce(as_code(value))


# ----------------------------------------------------------------------------
# Scott ordering

bool_values = (error, undefined, true, false)


@for_each([
    (x, y, lib.equal(x, y)),
    (quote(x), quote(x), true),
    (quote(undefined), quote(error), false),
    (quote(error), quote(undefined), false),
    (error, x, error),
    (x, error, error),
    (undefined, x, lib.equal(undefined, x)),
    (x, undefined, lib.equal(x, undefined)),
    (undefined, quote(x), undefined),
    (quote(x), undefined, undefined),
    (quote(error), quote(error), true),
    (quote(undefined), quote(undefined), true),
    (quote(zero), quote(zero), true),
    (quote(one), quote(one), true),
    (quote(two), quote(two), true),
    (quote(three), quote(three), true),
    (quote(error), quote(undefined), false),
    (quote(error), quote(zero), false),
    (quote(error), quote(one), false),
    (quote(error), quote(two), false),
    (quote(error), quote(three), false),
    (quote(undefined), quote(zero), false),
    (quote(undefined), quote(one), false),
    (quote(undefined), quote(two), false),
    (quote(undefined), quote(three), false),
    (quote(zero), quote(one), false),
    (quote(zero), quote(two), false),
    (quote(zero), quote(three), false),
    (quote(one), quote(two), false),
    (quote(one), quote(three), false),
    (quote(two), quote(three), false),
    (quote(true), quote(app(I, true)), true),
    (quote(false), quote(app(I, false)), true),
    pytest.mark.xfail((quote(J), quote(app(I, J)), true)),
])
def test_equal(x, y, expected):
    assert simplify(lib.equal(x, y)) == expected


@hypothesis.given(s_quoted)
def test_equal_reflexive(x):
    equal_xx = simplify(lib.equal(x, x))
    assert equal_xx == true


@hypothesis.given(s_quoted, s_quoted)
def test_equal_symmetric(x, y):
    hypothesis.assume(x is not y)
    equal_xy = simplify(lib.equal(x, y))
    equal_yx = simplify(lib.equal(y, x))
    hypothesis.assume(equal_xy in bool_values)
    hypothesis.assume(equal_yx in bool_values)
    assert equal_xy is equal_yx


@hypothesis.given(s_quoted, s_quoted, s_quoted)
def test_equal_transitive(x, y, z):
    # hypothesis.assume(x is not y and x is not z and y is not z)
    equal_xy = simplify(lib.equal(x, y))
    hypothesis.assume(equal_xy in bool_values)
    equal_yz = simplify(lib.equal(y, z))
    hypothesis.assume(equal_yz in bool_values)
    equal_xz = simplify(lib.equal(x, z))
    hypothesis.assume(equal_xz in bool_values)
    if equal_xy is true and equal_yz is true:
        assert equal_xz is true
    if equal_xz is false:
        assert equal_xy is false or equal_yz is false


@for_each([
    (x, y, lib.less(x, y)),
    (quote(x), quote(x), true),
    (quote(undefined), quote(error), true),
    (quote(error), quote(undefined), false),
    (error, x, error),
    (x, error, error),
    (undefined, x, lib.less(undefined, x)),
    (x, undefined, lib.less(x, undefined)),
    (undefined, quote(x), lib.less(undefined, quote(x))),
    (quote(x), undefined, lib.less(quote(x), undefined)),
    (undefined, quote(error), true),
    (quote(undefined), undefined, true),
    (quote(error), quote(error), true),
    (quote(error), quote(undefined), false),
    (quote(error), quote(zero), false),
    (quote(error), quote(one), false),
    (quote(error), quote(two), false),
    (quote(error), quote(three), false),
    (quote(undefined), quote(error), true),
    (quote(undefined), quote(undefined), true),
    (quote(undefined), quote(zero), true),
    (quote(undefined), quote(one), true),
    (quote(undefined), quote(two), true),
    (quote(undefined), quote(three), true),
    (quote(zero), quote(error), true),
    (quote(zero), quote(undefined), false),
    (quote(zero), quote(zero), true),
    (quote(zero), quote(one), false),
    (quote(zero), quote(two), false),
    (quote(zero), quote(three), false),
    (quote(one), quote(error), true),
    (quote(one), quote(undefined), false),
    (quote(one), quote(zero), false),
    (quote(one), quote(one), true),
    (quote(one), quote(two), false),
    (quote(one), quote(three), false),
    (quote(two), quote(error), true),
    (quote(two), quote(undefined), false),
    (quote(two), quote(zero), false),
    (quote(two), quote(one), false),
    (quote(two), quote(two), true),
    (quote(two), quote(three), false),
    (quote(three), quote(error), true),
    (quote(three), quote(undefined), false),
    (quote(three), quote(zero), false),
    (quote(three), quote(one), false),
    (quote(three), quote(two), false),
    (quote(three), quote(three), true),
])
def test_less(x, y, expected):
    assert simplify(lib.less(x, y)) == expected


@hypothesis.given(s_quoted)
def test_less_reflexive(x):
    less_xx = simplify(lib.less(x, x))
    assert less_xx == true


@pytest.mark.xfail(reason='{J} != {I J}')
@hypothesis.given(s_quoted, s_quoted)
def test_less_antisymmetric(x, y):
    hypothesis.assume(x is not y)
    less_xy = simplify(lib.less(x, y))
    less_yx = simplify(lib.less(y, x))
    equal_xy = simplify(lib.equal(x, y))
    hypothesis.assume(less_xy in bool_values)
    hypothesis.assume(less_yx in bool_values)
    if less_xy is true and less_yx is true:
        assert equal_xy is true
    if equal_xy is false:
        assert less_xy is not true or less_yx is not true


@hypothesis.given(s_quoted, s_quoted, s_quoted)
def test_less_transitive(x, y, z):
    # hypothesis.assume(x is not y and x is not z and y is not z)
    less_xy = simplify(lib.less(x, y))
    hypothesis.assume(less_xy in bool_values)
    less_yz = simplify(lib.less(y, z))
    hypothesis.assume(less_yz in bool_values)
    less_xz = simplify(lib.less(x, z))
    hypothesis.assume(less_xz in bool_values)
    if less_xy is true and less_yz is true:
        assert less_xz is true
    if less_xz is false:
        assert less_xy is not true or less_yz is not true


# ----------------------------------------------------------------------------
# Byte

BYTE_EXAMPLES = sorted(lib.byte_table.items())


@for_each([
    (ok, 8 * [true]),
    (ok, 8 * [false]),
    (ok, 7 * [true] + [false]),
    (ok, 7 * [false] + [true]),
    (ok, [true] + 7 * [false]),
    (ok, [false] + 7 * [true]),
    (undefined, 8 * [undefined]),
    (undefined, [undefined] + 7 * [true]),
    (undefined, [undefined] + 7 * [false]),
    (undefined, 7 * [true] + [undefined]),
    (undefined, 7 * [false] + [undefined]),
    (error, [error] + 7 * [true]),
    (error, [error] + 7 * [false]),
    (error, [error] + 7 * [undefined]),
    (error, 7 * [true] + [error]),
    (error, 7 * [false] + [error]),
    (error, 7 * [undefined] + [error]),
])
def test_byte_test(expected, bits):
    byte = lib.byte_make(*bits)
    assert reduce(lib.byte_test(byte)) == expected


@for_each(BYTE_EXAMPLES)
def test_byte_test_ok(n, byte):
    assert reduce(lib.byte_test(byte)) == ok


@for_each(BYTE_EXAMPLES)
def test_byte_make(n, expected):
    bits = [true if (n & (1 << i)) else false for i in xrange(8)]
    assert lib.byte_make(*bits) == expected


@for_each(BYTE_EXAMPLES)
def test_byte_get_bit(n, byte):
    for i in xrange(8):
        expected = true if (n & (1 << i)) else false
        assert simplify(lib.byte_get_bit[i](byte)) == expected
