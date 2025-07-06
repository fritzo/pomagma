import hypothesis
import pytest

from pomagma.reducer import lib
from pomagma.reducer.bohm import B, C, I, K, S, reduce, simplify, try_decide_less
from pomagma.reducer.bohm_test import s_quoted
from pomagma.reducer.sugar import app, as_term, combinator, join_, quote
from pomagma.reducer.syntax import APP, BOT, NVAR, SEMI, TOP, UNIT, sexpr_print
from pomagma.util import TRAVIS_CI
from pomagma.util.testing import for_each, xfail_param

pretty = sexpr_print


class lazy_actual_vs_expected:
    def __init__(self, actual, expected):
        self.actual = actual
        self.expected = expected

    def __str__(self):
        actual = pretty(self.actual)
        expected = pretty(self.expected)
        return f"\nActual: {actual}\nExpected: {expected}"

    __repr__ = __str__


f = NVAR("f")
w = NVAR("w")
x = NVAR("x")
y = NVAR("y")
z = NVAR("z")

ok = lib.ok
error = lib.error
undefined = lib.undefined
true = lib.true
false = lib.false
join = lib.join
compose = lib.compose


@for_each(
    [
        ("ok", lambda x: x),
        ("true", lambda x, y: x),
        ("false", lambda x, y: y),
        ("none", lambda f, g: f),
        ("some", lambda x, f, g: app(g, x)),
        ("pair", lambda x, y, f: app(f, x, y)),
        ("inl", lambda x, f, g: app(f, x)),
        ("inr", lambda y, f, g: app(g, y)),
        ("zero", lambda z, s: z),
        ("succ", lambda n, z, s: app(s, n)),
        ("nil", lambda n, c: n),
        ("cons", lambda head, tail, n, c: app(c, head, tail)),
    ]
)
def test_intro_forms(name, native):
    assert as_term(getattr(lib, name)) == as_term(native)


################################################################
# Semi-boolean type


@for_each(
    [
        (ok, ok),
        (error, error),
        (undefined, undefined),
        (true, error),
        (false, error),
        (join, error),
        (x, APP(SEMI, x)),
    ]
)
def test_semi_type(x, expected):
    assert simplify(lib.semi_type(x)) == expected


@for_each(
    [
        (ok, ok),
        (error, error),
        (undefined, undefined),
        (true, error),
        (false, error),
        (join, error),
        (x, APP(SEMI, x)),
    ]
)
def test_semi_test(x, expected):
    assert simplify(lib.semi_test(x)) == expected


@for_each(
    [
        (ok, ok, ok),
        (ok, undefined, ok),
        (undefined, ok, ok),
        (undefined, undefined, undefined),
        (ok, true, error),
        (ok, false, error),
        (true, ok, error),
        (false, ok, error),
    ]
)
def test_semi_join(x, y, expected):
    assert simplify(lib.semi_join(x, y)) == expected


@for_each(
    [
        (ok, ok, ok),
        (ok, undefined, undefined),
        (undefined, ok, undefined),
        (undefined, undefined, undefined),
        (ok, true, error),
        (ok, false, error),
        (true, ok, error),
        (false, ok, error),
    ]
)
def test_semi_meet(x, y, expected):
    assert simplify(lib.semi_meet(x, y)) == expected


@for_each(
    [
        (ok, quote(ok)),
        (undefined, undefined),
        (error, error),
        (true, error),
        (false, error),
    ]
)
def test_semi_quote(x, expected):
    assert simplify(lib.semi_quote(x)) == expected


@for_each(
    [
        (ok, true),
        (undefined, true),
        (error, false),
        (true, false),
        (false, false),
    ]
)
def test_enum_semi(y, expected):
    qxs = quote(lib.enum_semi)
    assert simplify(lib.enum_contains(qxs, quote(y))) == expected


################################################################
# Unit


@for_each(
    [
        (ok, ok),
        (error, error),
        (undefined, ok),
        (true, error),
        (false, error),
        (join, error),
        (x, APP(UNIT, x)),
    ]
)
def test_unit_type(x, expected):
    assert simplify(lib.unit_type(x)) == expected


@for_each(
    [
        (ok, ok),
        (error, error),
        (undefined, ok),
        (true, error),
        (false, error),
        (join, error),
        (x, APP(UNIT, x)),
    ]
)
def test_unit_test(x, expected):
    assert simplify(lib.unit_test(x)) == expected


@for_each(
    [
        (ok, ok, ok),
        (ok, undefined, ok),
        (undefined, ok, ok),
        (undefined, undefined, ok),
        (ok, true, error),
        (ok, false, error),
        (true, ok, error),
        (false, ok, error),
    ]
)
def test_unit_and(x, y, expected):
    assert simplify(lib.unit_and(x, y)) == expected


@for_each(
    [
        (ok, ok, ok),
        (ok, undefined, ok),
        (undefined, ok, ok),
        (undefined, undefined, ok),
        (ok, true, error),
        (ok, false, error),
        (true, ok, error),
        (false, ok, error),
    ]
)
def test_unit_or(x, y, expected):
    assert simplify(lib.unit_or(x, y)) == expected


@for_each(
    [
        (ok, quote(ok)),
        (undefined, quote(ok)),
        (error, error),
        (true, error),
        (false, error),
    ]
)
def test_unit_quote(x, expected):
    assert simplify(lib.unit_quote(x)) == expected


@for_each(
    [
        (ok, true),
        (undefined, true),
        (error, false),
        (true, false),
        (false, false),
    ]
)
def test_enum_unit(y, expected):
    qxs = quote(lib.enum_unit)
    assert simplify(lib.enum_contains(qxs, quote(y))) == expected


################################################################
# Boolean type


@for_each(
    [
        (true, true),
        (false, false),
        (error, error),
        (undefined, undefined),
        (ok, error),
        (join, error),
    ]
)
def test_bool_type(x, expected):
    assert simplify(lib.bool_type(x)) == expected


@for_each(
    [
        (true, ok),
        (false, ok),
        (error, error),
        (undefined, undefined),
        (ok, error),
        (join, error),
    ]
)
def test_bool_test(x, expected):
    assert simplify(lib.bool_test(x)) == expected


@for_each(
    [
        (true, false),
        (false, true),
        (undefined, undefined),
        (error, error),
        (ok, error),
        (join, error),
    ]
)
def test_bool_not(x, expected):
    assert simplify(lib.bool_not(x)) == expected


@for_each(
    [
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
        (join, true, error),
        (join, false, error),
        (true, join, error),
        (false, join, error),
    ]
)
def test_bool_and(x, y, expected):
    assert reduce(lib.bool_and(x, y)) == expected


@for_each(
    [
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
        (join, true, error),
        (join, false, error),
        (true, join, error),
        (false, join, error),
    ]
)
def test_bool_or(x, y, expected):
    assert reduce(lib.bool_or(x, y)) == expected


@for_each(
    [
        (true, quote(true)),
        (false, quote(false)),
        (undefined, undefined),
        (error, error),
        (ok, error),
        (join, error),
    ]
)
def test_bool_quote(x, expected):
    assert simplify(lib.bool_quote(x)) == expected


@for_each(
    [
        (error, error),
        (undefined, undefined),
        (true, ok),
        (false, undefined),
        (ok, error),
    ]
)
def test_bool_if_true(x, expected):
    assert simplify(lib.bool_if_true(x)) == expected


@for_each(
    [
        (error, error),
        (undefined, undefined),
        (true, undefined),
        (false, ok),
        (ok, error),
    ]
)
def test_bool_if_false(x, expected):
    assert simplify(lib.bool_if_false(x)) == expected


@for_each(
    [
        (true, true),
        (false, true),
        (join, false),
        (undefined, true),
        (error, false),
        (ok, false),
    ]
)
def test_enum_bool(y, expected):
    qxs = quote(lib.enum_bool)
    assert simplify(lib.enum_contains(qxs, quote(y))) == expected


################################################################
# Maybe type


@for_each(
    [
        (lib.none, lib.none),
        (lib.some(undefined), lib.some(undefined)),
        (lib.some(error), lib.some(error)),
        (lib.some(ok), lib.some(ok)),
        (lib.some(true), lib.some(true)),
        (lib.some(false), lib.some(false)),
        (error, error),
        (undefined, undefined),
        (ok, error),
        (join, error),
        (join_(lib.none, lib.some(undefined)), error),
        (join_(lib.some(true), lib.some(false)), lib.some(join)),
    ]
)
def test_maybe_type(x, expected):
    assert simplify(lib.maybe_type(x)) == expected


@for_each(
    [
        (lib.none, ok),
        (lib.some(x), ok),
        (error, error),
        (undefined, undefined),
    ]
)
def test_maybe_test(x, expected):
    assert simplify(lib.maybe_test(x)) == expected


@for_each(
    [
        (lib.none, quote(lib.none)),
        (lib.some(true), quote(lib.some(true))),
        (undefined, undefined),
        (error, error),
    ]
)
def test_maybe_quote(x, expected):
    quote_some = lib.bool_quote
    assert simplify(lib.maybe_quote(quote_some, x)) == expected


@for_each(
    [
        (lib.enum_unit, lib.none, true),
        (lib.enum_unit, undefined, true),
        (lib.enum_unit, error, false),
        (lib.enum_unit, lib.some(ok), true),
        (lib.enum_unit, lib.some(undefined), true),
        (lib.enum_unit, lib.some(error), false),
    ]
)
def test_enum_maybe(enum_item, y, expected):
    qxs = quote(lib.enum_maybe(enum_item))
    assert simplify(lib.enum_contains(qxs, quote(y))) == expected


################################################################
# Products

xy = lib.pair(x, y)


@for_each(
    [
        (xy, ok),
        (error, error),
        (undefined, undefined),
    ]
)
def test_prod_test(x, expected):
    assert simplify(lib.prod_test(x)) == expected


@for_each(
    [
        (xy, x),
        (error, error),
        (undefined, undefined),
    ]
)
def test_prod_fst(x, expected):
    assert simplify(lib.prod_fst(x)) == expected


@for_each(
    [
        (xy, y),
        (error, error),
        (undefined, undefined),
    ]
)
def test_prod_snd(x, expected):
    assert simplify(lib.prod_snd(x)) == expected


@for_each(
    [
        (lib.pair(ok, false), quote(lib.pair(ok, false))),
        (undefined, undefined),
        (error, error),
    ]
)
def test_prod_quote(x, expected):
    quote_fst = lib.unit_quote
    quote_snd = lib.bool_quote
    assert simplify(lib.prod_quote(quote_fst, quote_snd, x)) == expected


@for_each(
    [
        (lib.enum_unit, lib.enum_bool, undefined, true),
        (lib.enum_unit, lib.enum_bool, error, false),
        (lib.enum_unit, lib.enum_bool, lib.pair(undefined, undefined), true),
        (lib.enum_unit, lib.enum_bool, lib.pair(ok, undefined), true),
        (lib.enum_unit, lib.enum_bool, lib.pair(undefined, true), true),
        (lib.enum_unit, lib.enum_bool, lib.pair(undefined, false), true),
        (lib.enum_unit, lib.enum_bool, lib.pair(ok, true), true),
        (lib.enum_unit, lib.enum_bool, lib.pair(ok, false), true),
        (lib.enum_unit, lib.enum_bool, lib.pair(undefined, error), false),
        (lib.enum_unit, lib.enum_bool, lib.pair(error, undefined), false),
    ]
)
def test_enum_prod(enum_fst, enum_snd, y, expected):
    qxs = quote(lib.enum_prod(enum_fst, enum_snd))
    assert simplify(lib.enum_contains(qxs, quote(y))) == expected


################################################################
# Sums


@for_each(
    [
        (lib.inl(x), ok),
        (lib.inr(y), ok),
        (error, error),
        (undefined, undefined),
    ]
)
def test_sum_test(x, expected):
    assert simplify(lib.sum_test(x)) == expected


@for_each(
    [
        (lib.inl(ok), quote(lib.inl(ok))),
        (lib.inr(true), quote(lib.inr(true))),
        (lib.inr(false), quote(lib.inr(false))),
        (undefined, undefined),
        (error, error),
    ]
)
def test_sum_quote(x, expected):
    quote_inl = lib.unit_quote
    quote_inr = lib.bool_quote
    assert simplify(lib.sum_quote(quote_inl, quote_inr, x)) == expected


@for_each(
    [
        (lib.enum_unit, lib.enum_bool, undefined, true),
        (lib.enum_unit, lib.enum_bool, error, false),
        (lib.enum_unit, lib.enum_bool, lib.inl(undefined), true),
        (lib.enum_unit, lib.enum_bool, lib.inl(ok), true),
        (lib.enum_unit, lib.enum_bool, lib.inl(error), false),
        (lib.enum_unit, lib.enum_bool, lib.inl(true), false),
        (lib.enum_unit, lib.enum_bool, lib.inl(false), false),
        (lib.enum_unit, lib.enum_bool, lib.inr(undefined), true),
        (lib.enum_unit, lib.enum_bool, lib.inr(true), true),
        (lib.enum_unit, lib.enum_bool, lib.inr(false), true),
        (lib.enum_unit, lib.enum_bool, lib.inr(ok), false),
        (lib.enum_unit, lib.enum_bool, lib.inr(error), false),
    ]
)
def test_enum_sum(enum_inl, enum_inr, y, expected):
    qxs = quote(lib.enum_sum(enum_inl, enum_inr))
    assert simplify(lib.enum_contains(qxs, quote(y))) == expected


################################################################
# Numerals as Y Maybe

succ = lib.succ
zero = lib.zero


def num(n):
    assert isinstance(n, int) and n >= 0
    result = zero
    for _ in range(n):
        result = succ(result)
    return result


@for_each(
    [
        (num(0), ok),
        (num(1), ok),
        (num(2), ok),
        (num(3), ok),
        (error, error),
        (succ(error), error),
        (succ(succ(error)), error),
        (succ(succ(succ(error))), error),
        (undefined, undefined),
        (succ(undefined), undefined),
        (succ(succ(undefined)), undefined),
        (succ(succ(succ(undefined))), undefined),
    ]
)
def test_num_test(x, expected):
    assert reduce(lib.num_test(x)) == expected


@for_each(
    [
        (num(0), true),
        (num(1), false),
        (num(2), false),
        (num(3), false),
        (undefined, undefined),
        (error, error),
    ]
)
def test_num_is_zero(x, expected):
    assert simplify(lib.num_is_zero(x)) == expected


@for_each(
    [
        (num(0), error),
        (num(1), num(0)),
        (num(2), num(1)),
        (num(3), num(2)),
        (undefined, undefined),
        (succ(undefined), undefined),
        (succ(succ(undefined)), succ(undefined)),
        (error, error),
        (succ(error), error),
        (succ(succ(error)), error),
    ]
)
def test_num_pred(x, expected):
    assert simplify(lib.num_pred(x)) == expected


@for_each(
    [
        (num(0), num(0), num(0 + 0)),
        (num(0), num(1), num(0 + 1)),
        (num(0), num(2), num(0 + 2)),
        (num(0), num(3), num(0 + 3)),
        (num(1), num(1), num(1 + 1)),
        (num(1), num(2), num(1 + 2)),
        (num(1), num(3), num(1 + 3)),
        (num(2), num(2), num(2 + 2)),
        (num(2), num(3), num(2 + 3)),
        (num(3), num(3), num(3 + 3)),
        (undefined, num(0), undefined),
        (num(0), undefined, undefined),
        (error, x, error),
        (x, error, error),
    ]
)
def test_num_add(x, y, expected):
    assert reduce(lib.num_add(x, y)) == expected


@for_each(
    [
        (num(0), num(0), num(0 * 0)),
        (num(0), num(1), num(0 * 1)),
        (num(0), num(2), num(0 * 2)),
        (num(0), num(3), num(0 * 3)),
        (num(1), num(1), num(1 * 1)),
        (num(1), num(2), num(1 * 2)),
        xfail_param(num(1), num(3), num(1 * 3)),
        xfail_param(num(2), num(2), num(2 * 2)),
        xfail_param(num(2), num(3), num(2 * 3)),
        xfail_param(num(3), num(3), num(3 * 3)),
        (undefined, num(0), num(0)),
        (num(0), undefined, num(0)),
        (error, x, error),
        (x, error, error),
    ]
)
def test_num_mul(x, y, expected):
    assert reduce(lib.num_mul(x, y)) == expected


@for_each(
    [
        (num(0), num(0), ok),
        (num(0), num(1), undefined),
        (num(0), num(2), undefined),
        (num(0), num(3), undefined),
        (num(1), num(0), undefined),
        (num(1), num(1), ok),
        (num(1), num(2), undefined),
        (num(1), num(3), undefined),
        (num(2), num(0), undefined),
        (num(2), num(1), undefined),
        (num(2), num(2), ok),
        (num(2), num(3), undefined),
        (num(3), num(0), undefined),
        (num(3), num(1), undefined),
        (num(3), num(2), undefined),
        (num(3), num(3), ok),
    ]
)
def test_num_if_eq(x, y, expected):
    assert reduce(lib.num_if_eq(x, y)) == expected


@for_each(
    [
        (num(0), num(0), true),
        (num(0), num(1), false),
        (num(0), num(2), false),
        (num(0), num(3), false),
        (num(1), num(0), false),
        (num(1), num(1), true),
        (num(1), num(2), false),
        (num(1), num(3), false),
        (num(2), num(0), false),
        (num(2), num(1), false),
        (num(2), num(2), true),
        (num(2), num(3), false),
        (num(3), num(0), false),
        (num(3), num(1), false),
        (num(3), num(2), false),
        (num(3), num(3), true),
    ]
)
def test_num_eq(x, y, expected):
    assert reduce(lib.num_eq(x, y)) == expected


@for_each(
    [
        (num(0), num(0), ok),
        (num(0), num(1), ok),
        (num(0), num(2), ok),
        (num(0), num(3), ok),
        (num(1), num(0), undefined),
        (num(1), num(1), ok),
        (num(1), num(2), ok),
        (num(1), num(3), ok),
        (num(2), num(0), undefined),
        (num(2), num(1), undefined),
        (num(2), num(2), ok),
        (num(2), num(3), ok),
        (num(3), num(0), undefined),
        (num(3), num(1), undefined),
        (num(3), num(2), undefined),
        (num(3), num(3), ok),
    ]
)
def test_num_if_le(x, y, expected):
    assert reduce(lib.num_if_le(x, y)) == expected


@for_each(
    [
        (num(0), num(0), true),
        (num(0), num(1), true),
        (num(0), num(2), true),
        (num(0), num(3), true),
        (num(1), num(0), false),
        (num(1), num(1), true),
        (num(1), num(2), true),
        (num(1), num(3), true),
        (num(2), num(0), false),
        (num(2), num(1), false),
        (num(2), num(2), true),
        (num(2), num(3), true),
        (num(3), num(0), false),
        (num(3), num(1), false),
        (num(3), num(2), false),
        (num(3), num(3), true),
    ]
)
def test_num_le(x, y, expected):
    assert reduce(lib.num_le(x, y)) == expected


@for_each(
    [
        (num(0), num(0), false),
        (num(0), num(1), true),
        (num(0), num(2), true),
        (num(0), num(3), true),
        (num(1), num(0), false),
        (num(1), num(1), false),
        (num(1), num(2), true),
        (num(1), num(3), true),
        (num(2), num(0), false),
        (num(2), num(1), false),
        (num(2), num(2), false),
        (num(2), num(3), true),
        (num(3), num(0), false),
        (num(3), num(1), false),
        (num(3), num(2), false),
        (num(3), num(3), false),
    ]
)
def test_num_lt(x, y, expected):
    assert reduce(lib.num_lt(x, y)) == expected


@for_each(
    [
        (num(0), succ, num(0), num(0)),
        (num(0), succ, num(1), num(1)),
        (num(0), succ, num(2), num(2)),
        (num(0), succ, num(3), num(3)),
        (num(1), succ, num(0), num(1)),
        (num(1), succ, num(1), num(2)),
        (num(1), succ, num(2), num(3)),
        (num(0), lambda x: succ(succ(x)), num(0), num(0)),
        (num(0), lambda x: succ(succ(x)), num(1), num(2)),
        (num(1), lambda x: succ(succ(x)), num(0), num(1)),
        (num(1), lambda x: succ(succ(x)), num(1), num(3)),
        (true, lambda x: false, num(0), true),
        (true, lambda x: false, num(1), false),
        (true, lambda x: false, num(2), false),
        (y, ok, num(0), y),
        (y, ok, num(1), y),
        (y, ok, num(2), y),
        (y, ok, num(3), y),
        (y, ok, undefined, undefined),
        (y, ok, error, error),
    ]
)
def test_num_rec(z, s, x, expected):
    assert reduce(lib.num_rec(z, s, x)) == expected


@for_each(
    [
        (num(0), quote(num(0))),
        (num(1), quote(num(1))),
        (num(2), quote(num(2))),
        (num(3), quote(num(3))),
        (undefined, undefined),
        (error, error),
    ]
)
def test_num_quote(x, expected):
    assert reduce(lib.num_quote(x)) == expected


@pytest.mark.parametrize(
    "y, expected",
    [
        (undefined, true),
        xfail_param(error, false),
        (zero, true),
        xfail_param(succ(undefined), true),
        xfail_param(succ(zero), true),
        xfail_param(succ(error), false),
        xfail_param(succ(succ(undefined)), true),
        xfail_param(succ(succ(zero)), true),
        xfail_param(succ(succ(error)), false),
        xfail_param(num(3), true),
        xfail_param(num(4), true),
    ],
)
def test_enum_num(y, expected):
    qxs = quote(lib.enum_num)
    assert simplify(lib.enum_contains(qxs, quote(y))) == expected


################################################################
# Finite homogeneous lists

nil = lib.nil
cons = lib.cons


def make_list(xs, end=nil):
    assert end in (nil, undefined, error)
    result = nil
    for x in reversed(xs):
        result = cons(x, result)
    return result


@for_each(
    [
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
    ]
)
def test_list_test(x, expected):
    assert reduce(lib.list_test(x)) == expected


@for_each(
    [
        (cons(x, nil), false),
        (cons(x, cons(y, nil)), false),
        (cons(x, cons(y, cons(z, nil))), false),
        (cons(x, error), false),
        (cons(x, undefined), false),
        (error, error),
        (undefined, undefined),
    ]
)
def test_list_empty(x, expected):
    assert simplify(lib.list_empty(x)) == expected


@for_each(
    [
        (nil, true),
        pytest.param(
            cons(true, nil), true, marks=pytest.mark.skipif(TRAVIS_CI, reason="wtf")
        ),
        (cons(false, nil), false),
        pytest.param(
            cons(true, cons(true, nil)),
            true,
            marks=pytest.mark.skipif(TRAVIS_CI, reason="wtf"),
        ),
        pytest.param(
            cons(true, cons(false, nil)),
            false,
            marks=pytest.mark.skipif(TRAVIS_CI, reason="wtf"),
        ),
        (cons(false, cons(true, nil)), false),
        (cons(false, cons(false, nil)), false),
    ]
)
def test_list_all(x, expected):
    assert reduce(lib.list_all(x)) == expected


@for_each(
    [
        (nil, false),
        (cons(true, nil), true),
        (cons(false, nil), false),
        (cons(true, cons(true, nil)), true),
        (cons(true, cons(false, nil)), true),
        (cons(false, cons(true, nil)), true),
        (cons(false, cons(false, nil)), false),
    ]
)
def test_list_any(x, expected):
    assert reduce(lib.list_any(x)) == expected


@for_each(
    [
        (nil, nil, nil),
        (cons(x, nil), nil, cons(x, nil)),
        (nil, cons(y, nil), cons(y, nil)),
        (cons(x, nil), cons(y, nil), cons(x, cons(y, nil))),
        (
            cons(w, nil),
            cons(x, cons(y, cons(z, nil))),
            cons(w, cons(x, cons(y, cons(z, nil)))),
        ),
        (
            cons(w, cons(x, nil)),
            cons(y, cons(z, nil)),
            cons(w, cons(x, cons(y, cons(z, nil)))),
        ),
        (
            cons(w, cons(x, cons(y, nil))),
            cons(z, nil),
            cons(w, cons(x, cons(y, cons(z, nil)))),
        ),
    ]
)
def test_list_cat(xs, ys, expected):
    assert reduce(lib.list_cat(xs, ys)) == expected


@for_each(
    [
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
    ]
)
def test_list_map(f, x, expected):
    assert reduce(lib.list_map(f, x)) == expected


@for_each(
    [
        (nil, cons, nil, nil),
        (nil, undefined, nil, nil),
        (nil, error, nil, nil),
        (nil, cons, cons(x, nil), cons(x, nil)),
        (nil, cons, cons(x, undefined), cons(x, undefined)),
        (nil, cons, cons(x, error), cons(x, error)),
    ]
)
def test_list_rec(n, c, x, expected):
    assert reduce(lib.list_rec(n, c, x)) == expected


@for_each(
    [
        (lib.bool_type, nil, nil),
        (lib.bool_type, cons(true, nil), cons(true, nil)),
        (lib.bool_type, cons(true, cons(false, nil)), cons(true, nil)),
        (lib.bool_type, cons(false, cons(true, nil)), cons(true, nil)),
        (lib.bool_type, cons(true, cons(true, nil)), cons(true, cons(true, nil))),
        (lib.bool_not, nil, nil),
        (lib.bool_not, cons(true, nil), nil),
        (lib.bool_not, cons(true, cons(false, nil)), cons(false, nil)),
        (lib.bool_not, cons(false, cons(true, nil)), cons(false, nil)),
        (lib.bool_not, cons(true, cons(true, nil)), nil),
        (
            lib.num_is_zero,
            cons(num(2), cons(num(0), cons(num(1), nil))),
            cons(num(0), nil),
        ),
    ]
)
def test_list_filter(p, xs, expected):
    assert reduce(lib.list_filter(p, xs)) == expected


def num_list(xs):
    result = nil
    for x in reversed(xs):
        result = cons(num(x), result)
    return result


SORT_EXAMPLES = [
    xfail_param([]),
    xfail_param([0]),
    xfail_param([1]),
    xfail_param([0, 0]),
    xfail_param([0, 1]),
    xfail_param([1, 0]),
    xfail_param([1, 1]),
    xfail_param([0, 0, 0]),
    xfail_param([0, 0, 1]),
    xfail_param([0, 1, 0]),
    xfail_param([1, 0, 0]),
    xfail_param([0, 1, 1]),
    xfail_param([1, 0, 1]),
    xfail_param([1, 1, 0]),
    xfail_param([0, 1, 2]),
    xfail_param([0, 2, 1]),
    xfail_param([1, 0, 2]),
    xfail_param([1, 2, 0]),
    xfail_param([2, 0, 1]),
    xfail_param([2, 1, 0]),
    xfail_param([0, 0, 0, 1]),
    xfail_param([0, 0, 1, 0]),
    xfail_param([0, 1, 0, 0]),
    xfail_param([1, 0, 0, 0]),
    xfail_param([0, 0, 1, 1]),
    xfail_param([0, 1, 0, 1]),
    xfail_param([0, 1, 1, 0]),
    xfail_param([1, 0, 0, 1]),
    xfail_param([1, 0, 1, 0]),
    xfail_param([1, 1, 0, 0]),
    xfail_param([0, 1, 2, 3]),
    xfail_param([1, 2, 3, 0]),
    xfail_param([2, 3, 0, 1]),
    xfail_param([3, 0, 1, 2]),
]


@pytest.mark.skip(reason="hangs")
@for_each(SORT_EXAMPLES)
def test_list_sort(list_):
    xs = num_list(list_)
    expected = num_list(sorted(list_))
    actual = reduce(lib.list_sort(lib.num_lt, xs))
    assert actual == expected, lazy_actual_vs_expected(actual, expected)


@for_each(
    [
        (error, error),
        (undefined, undefined),
        (nil, num(0)),
        (cons(x, nil), num(1)),
        (cons(error, nil), num(1)),
        (cons(undefined, nil), num(1)),
        (cons(x, cons(y, nil)), num(2)),
        (cons(error, cons(undefined, nil)), num(2)),
        (cons(undefined, cons(error, nil)), num(2)),
        (cons(x, cons(y, cons(z, nil))), num(3)),
        (cons(error, cons(undefined, cons(error, nil))), num(3)),
        (cons(undefined, cons(error, cons(undefined, nil))), num(3)),
        (cons(error, undefined), succ(undefined)),
        (cons(error, cons(error, undefined)), succ(succ(undefined))),
    ]
)
def test_list_size(xs, expected):
    assert reduce(lib.list_size(xs)) == expected


@for_each(
    [
        (nil, quote(nil)),
        xfail_param(cons(num(0), nil), quote(cons(num(0), nil))),
        xfail_param(cons(num(1), nil), quote(cons(num(1), nil))),
        xfail_param(cons(num(2), nil), quote(cons(num(2), nil))),
        xfail_param(cons(num(3), nil), quote(cons(num(3), nil))),
        xfail_param(
            cons(num(2), cons(num(0), nil)),
            quote(cons(num(2), cons(num(0), nil))),
        ),
        (undefined, undefined),
        (error, error),
    ]
)
def test_list_quote(x, expected):
    quote_item = lib.num_quote
    assert reduce(lib.list_quote(quote_item, x)) == expected


@for_each(
    [
        (lib.enum_bool, undefined, true),
        xfail_param(lib.enum_bool, error, false),
        (lib.enum_bool, nil, true),
        (lib.enum_bool, cons(undefined, undefined), true),
        (lib.enum_bool, cons(true, undefined), true),
        (lib.enum_bool, cons(false, undefined), true),
        (lib.enum_bool, cons(true, nil), true),
        (lib.enum_bool, cons(true, nil), true),
        xfail_param(lib.enum_bool, cons(undefined, error), false),
        xfail_param(lib.enum_bool, cons(error, undefined), false),
        xfail_param(lib.enum_unit, cons(ok, cons(ok, nil)), true),
        xfail_param(lib.enum_unit, cons(ok, cons(ok, undefined)), true),
        xfail_param(lib.enum_unit, cons(ok, cons(ok, error)), false),
    ]
)
def test_enum_list(enum_item, y, expected):
    qxs = quote(lib.enum_list(enum_item))
    assert simplify(lib.enum_contains(qxs, quote(y))) == expected


################################################################
# Streams


def make_stream(xs, limit):
    result = lib.stream_const(limit)
    for x in reversed(xs):
        result = lib.stream_cons(x, result)
    return result


@for_each(
    [
        (BOT, BOT, I),
        (app(K, I), BOT, I),
        xfail_param(TOP, BOT, TOP),
        xfail_param(BOT, lib.stream_bot, I),
        xfail_param(app(K, I), lib.stream_bot, I),
        (TOP, lib.stream_bot, TOP),
        xfail_param(I, lib.stream_bot, BOT),
        xfail_param(I, make_stream([I], BOT), I),
        xfail_param(I, make_stream([BOT, I], BOT), I),
        xfail_param(I, make_stream([BOT, BOT, I], BOT), I),
        xfail_param(I, make_stream([K], BOT), TOP),
        (I, make_stream([TOP], BOT), TOP),
        xfail_param(I, make_stream([BOT, TOP], BOT), TOP),
        xfail_param(I, make_stream([BOT, BOT, TOP], BOT), TOP),
    ]
)
def test_stream_test(test_item, xs, expected):
    assert reduce(lib.stream_test(test_item, xs)) is expected


@pytest.mark.xfail(reason="FIXME")
@for_each([TOP, BOT, I, K, B, C, S, x, x | y, S(I, I)])
def test_stream_const(x):
    expected = lib.stream_const(x)
    actual = simplify(lib.stream_cons(x, lib.stream_const(x)))
    assert actual is expected


@for_each(
    [
        (BOT, BOT),
        xfail_param(lib.stream_bot, BOT),
        (lib.stream_const(TOP), TOP),
        xfail_param(lib.stream_const(I), I),
        xfail_param(lib.stream_const(K), K),
        xfail_param(lib.stream_const(B), B),
        xfail_param(lib.stream_const(S), S),
        xfail_param(lib.stream_const(x), x),
        xfail_param(lib.stream_cons(BOT, lib.stream_const(x)), x),
        xfail_param(lib.stream_cons(x, lib.stream_const(BOT)), x),
        xfail_param(lib.stream_cons(BOT, lib.stream_cons(BOT, lib.stream_const(x))), x),
        xfail_param(
            lib.stream_cons(BOT, lib.stream_cons(x, lib.stream_bot)),
            x,
        ),
        xfail_param(
            lib.stream_cons(x, lib.stream_cons(y, lib.stream_bot)),
            x | y,
        ),
    ]
)
def test_stream_join(xs, expected):
    assert simplify(lib.stream_join(xs)) is expected


@pytest.mark.xfail(reason="FIXME")
@for_each(
    [
        (I, lib.stream_bot, lib.stream_bot),
        (TOP, lib.stream_bot, lib.stream_const(TOP)),
        (BOT, lib.stream_const(TOP), lib.stream_bot),
        (lib.bool_not, lib.stream_const(true), lib.stream_const(false)),
        (lib.bool_not, lib.stream_const(false), lib.stream_const(true)),
        (
            succ,
            make_stream(list(map(num, [2, 0, 1])), BOT),
            make_stream(list(map(num, [3, 1, 2])), succ(BOT)),
        ),
    ]
)
def test_stream_map(f, xs, expected):
    assert reduce(lib.stream_map(f, xs)) is expected


@pytest.mark.xfail(reason="FIXME")
@for_each(
    [
        (
            [I, K, B],
            [true, false, true],
            [lib.pair(I, true), lib.pair(K, false), lib.pair(B, true)],
        ),
    ]
)
def test_stream_zip(xs, ys, expected):
    xs = make_stream(xs, BOT)
    ys = make_stream(ys, BOT)
    expected = make_stream(expected, BOT)
    assert lib.stream_zip(xs, ys) is expected


@pytest.mark.xfail(reason="FIXME")
@for_each(
    [
        ([I, K, B, C], [true, false, true], [I, true, K, false, B, true, C]),
    ]
)
def test_stream_dovetail(xs, ys, expected):
    xs = make_stream(xs, BOT)
    ys = make_stream(ys, BOT)
    expected = make_stream(expected, BOT)
    assert lib.stream_dovetail(xs, ys) is expected


@pytest.mark.xfail(reason="FIXME")
@for_each(
    [
        (lib.bool_quote, make_stream([true, false], true)),
        (lib.num_quote, make_stream([num(2), num(1)], num(0))),
    ]
)
def test_stream_quote(quote_item, xs):
    assert lib.stream_quote(quote_item, xs) is quote(xs)


@pytest.mark.xfail(reason="FIXME")
@for_each(
    [
        (lib.enum_unit, lib.stream_const(BOT)),
        (lib.enum_unit, lib.stream_const(I)),
        (lib.enum_bool, lib.stream_const(BOT)),
        (lib.enum_bool, lib.stream_const(true)),
        (lib.enum_bool, lib.stream_const(false)),
        (
            lib.enum_bool,
            lib.stream_dovetail(lib.stream_const(true), lib.stream_const(false)),
        ),
        (lib.enum_num, lib.stream_const(BOT)),
        (lib.enum_num, lib.stream_const(zero)),
        (lib.enum_num, lib.stream_num),
    ]
)
def test_stream_enum(enum_item, expected_lb):
    actual = lib.stream_enum(enum_item)
    assert try_decide_less(expected_lb, actual) is not False


@pytest.mark.xfail(reason="FIXME")
@for_each(list(range(10)))
def test_stream_num(index):
    expected = zero
    xs = lib.stream_num
    for _ in range(index):
        expected = succ(expected)
        xs = lib.stream_tail(xs)
    assert lib.stream_head(xs) is expected


@pytest.mark.xfail(reason="FIXME")
@for_each(list(range(10)))
def test_stream_take(size):
    expected = nil
    for n in reversed(list(range(size))):
        expected = cons(num(n), expected)
    assert lib.stream_take(lib.stream_num(num(size))) is expected


################################################################
# Enumerable sets

box = lib.box
enum = lib.enum


@for_each(
    [
        (enum([]), undefined),
        (enum([error]), box(error)),
        (enum([undefined]), box(undefined)),
        (enum([x]), box(x)),
        (enum([x, y]), join_(box(x), box(y))),
        (enum([x, y, z]), join_(box(x), box(y), box(z))),
    ]
)
def test_enum(actual, expected):
    assert actual == expected


@for_each(
    [
        (error, error),
        (undefined, undefined),
        (box(undefined), ok),
        (box(error), ok),
        (join_(box(true), box(false)), ok),
    ]
)
def test_enum_test(xs, expected):
    assert reduce(lib.enum_test(xs)) == expected


@for_each(
    [
        (undefined, undefined, undefined),
        (undefined, error, error),
        (error, undefined, error),
        (box(x), undefined, box(x)),
        (undefined, box(x), box(x)),
        (box(x), box(x), box(x)),
        (box(x), box(y), join_(box(x), box(y))),
    ]
)
def test_enum_union(xs, ys, expected):
    assert reduce(lib.enum_union(xs, ys)) == expected


@for_each(
    [
        (undefined, undefined),
        (error, error),
        (box(undefined), undefined),
        (box(error), error),
        (box(ok), ok),
        (box(true), error),
        (box(false), error),
    ]
)
def test_enum_any(xs, expected):
    assert reduce(lib.enum_any(xs)) == expected


@for_each(
    [
        (lib.semi_type, undefined, undefined),
        (lib.semi_type, error, error),
        (lib.semi_type, box(undefined), undefined),
        (lib.semi_type, box(ok), box(ok)),
        (lib.bool_if_true, undefined, undefined),
        (lib.bool_if_true, box(true), box(true)),
        (lib.bool_if_true, box(false), undefined),
        (lib.bool_if_true, join_(box(false), box(true)), box(true)),
        (lib.bool_if_false, undefined, undefined),
        (lib.bool_if_false, box(true), undefined),
        (lib.bool_if_false, box(false), box(false)),
        (lib.bool_if_false, join_(box(false), box(true)), box(false)),
    ]
)
def test_enum_filter(p, xs, expected):
    assert reduce(lib.enum_filter(p, xs)) == expected


@for_each(
    [
        (lib.semi_type, undefined, undefined),
        (lib.semi_type, error, error),
        (lib.semi_type, box(undefined), box(undefined)),
        (lib.semi_type, box(error), box(error)),
        (lib.semi_type, box(ok), box(ok)),
        (lib.semi_type, box(true), box(error)),
        (lib.semi_type, box(false), box(error)),
        (lib.bool_not, box(true), box(false)),
        (lib.bool_not, box(false), box(true)),
        (succ, undefined, undefined),
        (succ, box(undefined), box(succ(undefined))),
        (succ, box(num(0)), box(num(1))),
        (succ, box(num(1)), box(num(2))),
        (succ, box(num(2)), box(num(3))),
        (succ, join_(box(num(0)), box(num(2))), join_(box(num(1)), box(num(3)))),
    ]
)
def test_enum_map(f, xs, expected):
    assert reduce(lib.enum_map(f, xs)) == expected


@for_each(
    [
        (undefined, undefined),
        (error, error),
        (box(undefined), undefined),
        (box(error), error),
        (box(box(undefined)), box(undefined)),
        (box(box(ok)), box(ok)),
        (box(box(true)), box(true)),
        (join_(box(box(true)), box(box(false))), join_(box(true), box(false))),
    ]
)
def test_enum_flatten(xs, expected):
    assert reduce(lib.enum_flatten(xs)) == expected


@combinator
def num_try_pred(n):
    return app(n, undefined, lambda px: px)


@pytest.mark.xfail(run=False, reason="does not terminate")
@for_each(
    [
        (undefined, enum([ok]), enum([ok])),
        (box, enum([ok]), enum([ok])),
        (error, enum([ok]), error),
        (lambda x: box(lib.bool_not), enum([undefined]), enum([undefined])),
        (lambda x: box(lib.bool_not), enum([true]), enum([true, false])),
        (lambda x: box(lib.bool_not), enum([false]), enum([true, false])),
        (lambda x: box(lib.bool_not), enum([ok]), enum([error])),
        (compose(box, num_try_pred), enum([undefined]), enum([undefined])),
        (compose(box, num_try_pred), enum([num(0)]), enum([num(0)])),
        (compose(box, num_try_pred), enum([num(1)]), enum([num(0), num(1)])),
        (
            compose(box, num_try_pred),
            enum([num(2)]),
            enum(list(map(num, list(range(3))))),
        ),
        (
            compose(box, num_try_pred),
            enum([num(3)]),
            enum(list(map(num, list(range(4))))),
        ),
        (
            compose(box, num_try_pred),
            enum([num(4)]),
            enum(list(map(num, list(range(5))))),
        ),
    ]
)
def test_enum_close(f, xs, expected):
    assert reduce(lib.enum_close(f, xs)) == simplify(expected)


################################################################
# Functions

fun_t = lib.fun_type
semi_t = lib.semi_type
bool_t = lib.bool_type
maybe_t = lib.maybe_type


@for_each(
    [
        (semi_t, semi_t, semi_t),
        (bool_t, bool_t, bool_t),
        (maybe_t, maybe_t, maybe_t),
        xfail_param(lib.bool_not, lib.bool_not, bool_t),
    ]
)
def test_compose(f, g, expected):
    assert reduce(as_term(compose(f, g))) == simplify(as_term(expected))


@for_each(
    [
        (semi_t, fun_t(semi_t, semi_t)),
        (lib.semi_test, fun_t(semi_t, semi_t)),
        (lib.semi_join, fun_t(semi_t, fun_t(semi_t, semi_t))),
        (lib.semi_meet, fun_t(semi_t, fun_t(semi_t, semi_t))),
        (lib.semi_quote, fun_t(semi_t, I)),
        (bool_t, fun_t(bool_t, bool_t)),
        (lib.bool_test, fun_t(bool_t, semi_t)),
        (lib.bool_not, fun_t(bool_t, bool_t)),
        (lib.bool_and, fun_t(bool_t, fun_t(bool_t, bool_t))),
        (lib.bool_or, fun_t(bool_t, fun_t(bool_t, bool_t))),
        (lib.bool_quote, fun_t(bool_t, I)),
        (maybe_t, fun_t(maybe_t, maybe_t)),
        (lib.maybe_test, fun_t(maybe_t, semi_t)),
        (lib.maybe_quote, fun_t(I, fun_t(maybe_t, I))),
    ]
)
def test_fun_type_fixes(value, type_):
    assert reduce(app(type_, value)) == reduce(as_term(value))


# succ implemented using fix.
succ_fix = lib.fix(lambda f, x: app(x, num(1), lambda px: succ(app(f, px))))


@for_each(
    [
        (app(succ_fix, error), error),
        (app(succ_fix, undefined), undefined),
        (app(succ_fix, num(0)), num(1)),
        (app(succ_fix, num(1)), num(2)),
        (app(succ_fix, num(2)), num(3)),
    ]
)
def test_fix(value, expected):
    assert pretty(reduce(value)) == pretty(expected)


@for_each(
    [
        xfail_param(error, error),
        (undefined, undefined),
        # TODO Add more examples.
    ]
)
def test_qfix(value, expected):
    assert pretty(reduce(lib.qfix(value))) == pretty(expected)


@pytest.mark.xfail(run=False, reason="does not terminate")
@for_each(
    [
        (lambda x: x, x, x),
        (undefined, x, x),
        (error, x, error),
        (lambda x: join_(x, y), x, join_(x, y)),
        (lib.bool_not, undefined, undefined),
        (lib.bool_not, true, error),
        (lib.bool_not, false, error),
        (app(lib.enum_map, lib.bool_not), undefined, undefined),
        (app(lib.enum_map, lib.bool_not), enum([undefined]), enum([undefined])),
        (app(lib.enum_map, lib.bool_not), enum([true]), enum([true, false])),
        (app(lib.enum_map, lib.bool_not), enum([false]), enum([true, false])),
        (app(lib.enum_map, lib.bool_not), enum([join]), enum([error])),
        (app(lib.enum_map, lib.bool_not), enum([ok]), enum([error])),
        (app(lib.enum_map, lib.bool_not), error, error),
    ]
)
def test_close(f, x, expected):
    assert reduce(app(lib.close(f), x)) == expected


################################################################
# Type constructor

a_div = app(lib.construct, lambda a: a)
a_unit = app(lib.construct, lambda a: app(lib.a_arrow, a, a))
a_boool = app(
    lib.construct,
    lambda a: app(lib.a_arrow, a, app(lib.a_arrow, a, a)),
)


@for_each(
    [
        xfail_param(BOT, BOT, reason="FIXME", run=False),
        (TOP, TOP),
        (I, TOP),
        (K, TOP),
        (B, TOP),
        (C, TOP),
        (S, TOP),
        (join, TOP),
        (app(K, I), TOP),
        (app(C, B), TOP),
        (app(C, I), TOP),
        (app(S, I), TOP),
    ]
)
def test_div(x, expected):
    assert reduce(lib.div(x)) == expected


@pytest.mark.timeout(1)
@for_each(
    [
        xfail_param(BOT, BOT, reason="FIXME", run=False),
        (TOP, TOP),
        xfail_param(I, TOP, reason="FIXME", run=False),
        xfail_param(K, TOP, reason="FIXME", run=False),
        xfail_param(B, TOP, reason="FIXME", run=False),
        xfail_param(C, TOP, reason="FIXME", run=False),
        xfail_param(S, TOP, reason="FIXME", run=False),
        xfail_param(join, TOP, reason="FIXME", run=False),
        xfail_param(app(K, I), TOP, reason="FIXME", run=False),
        xfail_param(app(C, B), TOP, reason="FIXME", run=False),
        xfail_param(app(C, I), TOP, reason="FIXME", run=False),
        xfail_param(app(S, I), TOP, reason="FIXME", run=False),
    ]
)
def test_div_constructed(x, expected):
    assert reduce(app(a_div, x)) == expected


@pytest.mark.timeout(1)
@for_each(
    [
        xfail_param(ok, ok, reason="FIXME"),
        (error, error),
        xfail_param(undefined, undefined, reason="FIXME"),
        (true, error),
        (false, error),
        (join, error),
        xfail_param(x, app(UNIT, x), reason="FIXME"),
    ]
)
def test_unit_constructed(x, expected):
    assert simplify(app(a_unit, x)) == expected


@pytest.mark.timeout(1)
@for_each(
    [
        xfail_param(true, true),
        xfail_param(false, false),
        (error, error),
        xfail_param(undefined, undefined),
        xfail_param(join, join),
        (I, error),
        (B, error),
        (C, error),
        (S, error),
    ]
)
def test_boool_constructed(x, expected):
    assert simplify(app(a_boool, x)) == expected


################################################################
# Scott ordering

bool_values = (error, undefined, true, false)


@for_each(
    [
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
        (quote(num(0)), quote(num(0)), true),
        (quote(num(1)), quote(num(1)), true),
        (quote(num(2)), quote(num(2)), true),
        (quote(num(3)), quote(num(3)), true),
        (quote(error), quote(undefined), false),
        (quote(error), quote(num(0)), false),
        (quote(error), quote(num(1)), false),
        (quote(error), quote(num(2)), false),
        (quote(error), quote(num(3)), false),
        (quote(undefined), quote(num(0)), false),
        (quote(undefined), quote(num(1)), false),
        (quote(undefined), quote(num(2)), false),
        (quote(undefined), quote(num(3)), false),
        (quote(num(0)), quote(num(1)), false),
        (quote(num(0)), quote(num(2)), false),
        (quote(num(0)), quote(num(3)), false),
        (quote(num(1)), quote(num(2)), false),
        (quote(num(1)), quote(num(3)), false),
        (quote(num(2)), quote(num(3)), false),
        (quote(true), quote(app(I, true)), true),
        (quote(false), quote(app(I, false)), true),
        (quote(join), quote(app(I, join)), true),
    ]
)
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
    hypothesis.assume(equal_xy in bool_values)
    equal_yx = simplify(lib.equal(y, x))
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
        assert equal_xy is not true or equal_yz is not true


LESS_EXAMPLES = [
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
    xfail_param(undefined, quote(error), true),
    xfail_param(quote(undefined), undefined, true),
    (quote(error), quote(error), true),
    (quote(error), quote(undefined), false),
    (quote(error), quote(num(0)), false),
    (quote(error), quote(num(1)), false),
    (quote(error), quote(num(2)), false),
    (quote(error), quote(num(3)), false),
    (quote(undefined), quote(error), true),
    (quote(undefined), quote(undefined), true),
    (quote(undefined), quote(num(0)), true),
    (quote(undefined), quote(num(1)), true),
    (quote(undefined), quote(num(2)), true),
    (quote(undefined), quote(num(3)), true),
    (quote(num(0)), quote(error), true),
    (quote(num(0)), quote(undefined), false),
    (quote(num(0)), quote(num(0)), true),
    (quote(num(0)), quote(num(1)), false),
    (quote(num(0)), quote(num(2)), false),
    (quote(num(0)), quote(num(3)), false),
    (quote(num(1)), quote(error), true),
    (quote(num(1)), quote(undefined), false),
    (quote(num(1)), quote(num(0)), false),
    (quote(num(1)), quote(num(1)), true),
    (quote(num(1)), quote(num(2)), false),
    (quote(num(1)), quote(num(3)), false),
    (quote(num(2)), quote(error), true),
    (quote(num(2)), quote(undefined), false),
    (quote(num(2)), quote(num(0)), false),
    (quote(num(2)), quote(num(1)), false),
    (quote(num(2)), quote(num(2)), true),
    (quote(num(2)), quote(num(3)), false),
    (quote(num(3)), quote(error), true),
    (quote(num(3)), quote(undefined), false),
    (quote(num(3)), quote(num(0)), false),
    (quote(num(3)), quote(num(1)), false),
    (quote(num(3)), quote(num(2)), false),
    (quote(num(3)), quote(num(3)), true),
]


@for_each(LESS_EXAMPLES)
def test_less(x, y, expected):
    assert simplify(lib.less(x, y)) == expected


@hypothesis.given(s_quoted)
def test_less_reflexive(x):
    less_xx = simplify(lib.less(x, x))
    assert less_xx == true


@hypothesis.given(s_quoted, s_quoted)
@hypothesis.example(quote(join), quote(app(I, join)))
def test_less_antisymmetric(x, y):
    less_xy = simplify(lib.less(x, y))
    less_yx = simplify(lib.less(y, x))
    equal_xy = simplify(lib.equal(x, y))
    print(f"LESS: {less_xy}, NLESS: {less_yx}, EQUAL: {equal_xy}")
    if less_xy is true and less_yx is true:
        assert equal_xy is true
    if equal_xy is false:
        assert less_xy is false or less_yx is false


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


@for_each(
    [
        ([], undefined, false),
        ([], error, false),
        ([], x, false),
        ([error], error, true),
        ([undefined], undefined, true),
        ([x], x, true),
        ([x], undefined, true),
        ([error], x, true),
        ([ok, x], undefined, true),
        ([ok, x], ok, true),
        ([ok, x], x, true),
    ]
)
def test_enum_contains(xs, y, expected):
    qxs = quote(enum(xs))
    qy = quote(y)
    assert reduce(lib.enum_contains(qxs, qy)) == expected


# ----------------------------------------------------------------------------
# Byte

BYTE_EXAMPLES = sorted(lib.byte_table.items())


@for_each(
    [
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
    ]
)
def test_byte_test(expected, bits):
    byte = lib.byte_make(*bits)
    assert reduce(lib.byte_test(byte)) == expected


@for_each(BYTE_EXAMPLES)
def test_byte_test_ok(n, byte):
    assert reduce(lib.byte_test(byte)) == ok


@for_each(BYTE_EXAMPLES)
def test_byte_make(n, expected):
    bits = [true if (n & (1 << i)) else false for i in range(8)]
    assert lib.byte_make(*bits) == expected


@for_each(BYTE_EXAMPLES)
def test_byte_get_bit(n, byte):
    for i in range(8):
        expected = true if (n & (1 << i)) else false
        assert simplify(lib.byte_get_bit[i](byte)) == expected
