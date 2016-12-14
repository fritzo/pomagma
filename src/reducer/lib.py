"""Standard library of combinators.

Intro forms are hand-optimized; see lib_test.py for lambda versions.

"""

from pomagma.reducer.code import APP, JOIN, TOP, BOT, I, K, B, C
from pomagma.reducer.code import QUOTE, EQUAL, LESS, UNIT, BOOL, MAYBE
from pomagma.reducer.sugar import app, join_, quote, qapp, let
from pomagma.reducer.sugar import combinator, typed, symmetric

CI = APP(C, I)


def COMP(lhs, rhs):
    return APP(APP(B, lhs), rhs)


# ----------------------------------------------------------------------------
# Nondeterminism

join = JOIN(K, APP(K, I))


# ----------------------------------------------------------------------------
# Errors

error = TOP
undefined = BOT


# ----------------------------------------------------------------------------
# Unit

ok = I


@combinator
def unit_type(x):
    return app(UNIT, x)


@combinator
def unit_test(x):
    return unit_type(x)


@combinator
@typed(unit_type, unit_type, unit_type)
@symmetric
def unit_and(x, y):
    return app(x, y)


@combinator
@typed(unit_type, unit_type, unit_type)
def unit_or(x, y):
    return join_(x, y)


@combinator
def unit_quote(x):
    x = unit_type(x)
    return app(x, QUOTE(ok))


enum_unit = APP(CI, ok)


# ----------------------------------------------------------------------------
# Bool

true = K
false = APP(K, I)


@combinator
def bool_type(x):
    return app(BOOL, x)


@combinator
@typed(bool_type, unit_type)
def bool_test(x):
    return app(x, ok, ok)


@combinator
@typed(bool_type, bool_type)
def bool_not(x):
    return app(x, false, true)


@combinator
@typed(bool_type, bool_type, bool_type)
@symmetric
def bool_and(x, y):
    return app(x, y, false)


@combinator
@typed(bool_type, bool_type, bool_type)
@symmetric
def bool_or(x, y):
    return app(x, true, y)


@combinator
def bool_quote(x):
    x = bool_type(x)
    return app(x, QUOTE(true), QUOTE(false))


@combinator
def bool_if_true(x):
    x = bool_type(x)
    return unit_type(app(x, ok, undefined))


@combinator
def bool_if_false(x):
    x = bool_type(x)
    return unit_type(app(x, undefined, ok))


enum_bool = join_(APP(CI, true), APP(CI, false))


# ----------------------------------------------------------------------------
# Maybe

none = K


@combinator
def some(arg):
    return APP(K, APP(CI, arg))


@combinator
def maybe_type(x):
    return app(MAYBE, x)


@combinator
def maybe_test(x):
    x = maybe_type(x)
    return unit_type(app(x, ok, lambda y: ok))


@combinator
def maybe_quote(quote_some, x):
    x = maybe_type(x)
    return app(
        x,
        QUOTE(none),
        lambda y: qapp(quote(some), app(quote_some, y)),
    )


@combinator
def enum_maybe(enum_item):
    return join_(box(none), enum_map(some, enum_item))


# ----------------------------------------------------------------------------
# Products

@combinator
def pair(x, y):
    return APP(APP(C, APP(CI, x)), y)


@combinator
def prod_test(xy):
    return unit_type(app(xy, lambda x, y: ok))


@combinator
def prod_fst(xy):
    return app(xy, lambda x, y: x)


@combinator
def prod_snd(xy):
    return app(xy, lambda x, y: y)


@combinator
def prod_quote(quote_fst, quote_snd, xy):
    return app(
        xy,
        lambda x, y: qapp(quote(pair), app(quote_fst, x), app(quote_snd, y)),
    )


@combinator
def enum_prod(enum_fst, enum_snd):
    return app(enum_fst, lambda x: app(enum_snd, lambda y: box(pair(x, y))))


# ----------------------------------------------------------------------------
# Sums

@combinator
def inl(x):
    return COMP(K, APP(CI, x))


@combinator
def inr(y):
    return APP(K, APP(CI, y))


@combinator
def sum_test(xy):
    return unit_type(app(xy, lambda x: ok, lambda y: ok))


@combinator
def sum_quote(quote_inl, quote_inr, xy):
    return app(
        xy,
        lambda x: qapp(quote(inl), app(quote_inl, x)),
        lambda y: qapp(quote(inr), app(quote_inr, y)),
    )


@combinator
def enum_sum(enum_inl, enum_inr):
    return join_(enum_map(inl, enum_inl), enum_map(inr, enum_inr))


# ----------------------------------------------------------------------------
# Numerals as Y Maybe

zero = none
succ = some


@combinator
def num_test(x):
    return unit_type(app(x, ok, num_test))


@combinator
def num_is_zero(x):
    return app(x, true, lambda px: false)


@combinator
def num_pred(x):
    return app(x, error, lambda px: px)


@combinator
@symmetric
def num_add(x, y):
    return app(y, x, lambda py: succ(num_add(x, py)))


@combinator
@symmetric
def num_mul(x, y):
    return num_rec(zero, lambda py: app(num_add, x, py), y)


@combinator
@symmetric
def num_eq(x, y):
    return app(x, app(y, true, lambda py: false), lambda px:
               app(y, false, lambda py: num_eq(px, py)))


@combinator
def num_le(x, y):
    return app(x, true, lambda px: app(y, false, lambda py: num_le(px, py)))


@combinator
def num_lt(x, y):
    return app(y, false, lambda py: app(x, true, lambda px: num_lt(px, py)))


@combinator
def num_rec(z, s, x):
    return app(x, z, lambda px: app(s, num_rec(z, s, px)))


@combinator
def num_quote(x):
    return app(x, QUOTE(zero), lambda px: qapp(quote(succ), num_quote(px)))


@combinator
def enum_num():
    return join_(box(zero), app(enum_map, succ, enum_num))


# ----------------------------------------------------------------------------
# Finite homogeneous lists

nil = K


@combinator
def cons(head, tail):
    return APP(K, APP(APP(C, APP(CI, head)), tail))


@combinator
def list_test(xs):
    return unit_type(app(xs, ok, lambda h, t: list_test(t)))


@combinator
def list_empty(xs):
    return app(xs, true, lambda h, t: false)


@combinator
def list_all(xs):
    return app(xs, true, lambda h, t: bool_and(h, list_all(t)))


@combinator
def list_any(xs):
    return app(xs, false, lambda h, t: bool_or(h, list_any(t)))


@combinator
def list_cat(xs, ys):
    return app(xs, ys, lambda h, t: cons(h, list_cat(t, ys)))


@combinator
def list_map(f, xs):
    return app(xs, nil, lambda h, t: cons(app(f, h), list_map(f, t)))


@combinator
def list_rec(n, c, xs):
    return app(xs, n, lambda h, t: app(c, h, list_rec(n, c, t)))


@combinator
def list_filter(p, xs):
    p = compose(bool_type, p)
    return list_rec(nil, lambda h, t: app(p, h, app(cons, h), I, t), xs)


@combinator
def list_size(xs):
    return app(xs, zero, lambda h, t: succ(list_size(t)))


@combinator
def list_sort(lt, xs):
    return let(
        app(list_sort, lt), lambda sort:
        app(xs, nil, lambda h, t:
            let(app(lt, h), lambda lt_h:
                app(list_cat,
                    app(sort, app(list_filter, lt_h, t)),
                    cons(h,
                         app(sort,
                             app(list_filter, compose(bool_not, lt_h), t)))))))


@combinator
def list_quote(quote_item, xs):
    return app(
        xs,
        QUOTE(nil),
        lambda h, t: qapp(quote(cons), app(quote_item, h), list_quote(t)),
    )


@combinator
def enum_list(enum_item):
    return join_(
        box(nil),
        app(enum_list(enum_item), lambda t:
            app(enum_item, lambda h: box(cons(h, t)))),
    )


# ----------------------------------------------------------------------------
# Enumerable sets

@combinator
def box(item):
    return app(CI, item)


def enum(items):
    assert isinstance(items, (list, set, frozenset)), items
    return join_(*map(box, items))


@combinator
def enum_test(xs):
    return unit_type(app(xs, lambda x: ok))


@combinator
def enum_union(xs, ys):
    return join_(xs, ys)


@combinator
def enum_any(xs):
    return unit_type(app(xs, unit_type))


@combinator
def enum_filter(p, xs):
    p = compose(unit_type, p)
    return app(xs, lambda x: app(p, x, box(x)))


@combinator
def enum_map(f, xs):
    return app(xs, lambda x: box(app(f, x)))


@combinator
def enum_flatten(xs):
    return app(xs, lambda x: x)


@combinator
def enum_close(f, xs):
    """forall a, (a -> enum a) -> enum a -> enum a."""
    # return app(close, lambda ys: app(ys, f), xs)
    return enum_union(xs, app(enum_close, f, xs, f))


# ----------------------------------------------------------------------------
# Functions

@combinator
def compose(f, g):
    return lambda x: app(f, app(g, x))


@combinator
def fun_type(domain_type, codomain_type):
    return lambda f, x: app(codomain_type, app(f, app(domain_type, x)))


@combinator
def fix(f):
    """The Y combinator."""
    return app(f, fix(f))


@combinator
def close(f):
    """Scott's universal closure operator V."""
    return lambda x: join_(x, app(f, close(x)))


# ----------------------------------------------------------------------------
# Type constructor

@combinator
def a_preconj(f):
    return app(f, lambda r, s: pair(app(B, r), app(B, s)))


@combinator
def a_postconj(f):
    return app(f, lambda r, s: pair(app(C, B, s), app(C, B, r)))


@combinator
def a_compose(f1, f2):
    return app(f1, lambda r1, s1: app(f2, lambda r2, s2: app(
        pair, compose(r1, r2), compose(s2, s1)),
    ))


@combinator
def div(f):
    return join_(f, app(div, f, TOP))


@combinator
def a_copy(f, x):
    return app(f, x, x)


@combinator
def a_join(f, x, y):
    return app(f, join_(x, y))


@combinator
def a_construct():
    return join_(
        app(pair, I, I),
        app(pair, BOT, TOP),
        app(pair, div, BOT),
        app(pair, a_copy, a_join),
        app(pair, C, C),
        app(a_preconj, a_construct),
        app(a_postconj, a_construct),
        app(a_compose, a_construct, a_construct),
    )


@combinator
def construct(f):
    """The simple type constructor, aka AAA."""
    return app(a_construct, f)


@construct
def a_arrow(a, b):
    return lambda f, x: app(b, app(f, app(a, x)))


# ----------------------------------------------------------------------------
# Scott ordering

@combinator
def equal(x, y):
    return bool_type(app(EQUAL, x, y))


@combinator
def less(x, y):
    return bool_type(app(LESS, x, y))


@combinator
def enum_contains(qxs, qy):
    return app(LESS, qapp(quote(box), qy), qxs)


# ----------------------------------------------------------------------------
# Byte as an 8-tuple of bits

def _make_bits_table(n):
    table = {0: I}
    for i in xrange(n):
        prev = table
        table = {}
        for k, v in prev.iteritems():
            table[k] = APP(APP(C, v), false)
            table[k | (1 << i)] = APP(APP(C, v), true)
    return table


byte_table = _make_bits_table(8)
assert len(byte_table) == 256


# FIXME this is very slow
def _bits_test(b0, b1, b2, b3, b4, b5, b6, b7):
    bits = [b0, b1, b2, b3, b4, b5, b6, b7]
    tests = map(bool_test, bits)
    return app(join_(*tests), *tests)


@combinator
def byte_test(x):
    return unit_type(app(x, _bits_test))


@combinator
def byte_make(b0, b1, b2, b3, b4, b5, b6, b7):
    result = I
    for b in (b0, b1, b2, b3, b4, b5, b6, b7):
        result = app(C, result, b)
    return result


byte_get_bit = [
    combinator(lambda x: app(x, lambda b0, b1, b2, b3, b4, b5, b6, b7: b0)),
    combinator(lambda x: app(x, lambda b0, b1, b2, b3, b4, b5, b6, b7: b1)),
    combinator(lambda x: app(x, lambda b0, b1, b2, b3, b4, b5, b6, b7: b2)),
    combinator(lambda x: app(x, lambda b0, b1, b2, b3, b4, b5, b6, b7: b3)),
    combinator(lambda x: app(x, lambda b0, b1, b2, b3, b4, b5, b6, b7: b4)),
    combinator(lambda x: app(x, lambda b0, b1, b2, b3, b4, b5, b6, b7: b5)),
    combinator(lambda x: app(x, lambda b0, b1, b2, b3, b4, b5, b6, b7: b6)),
    combinator(lambda x: app(x, lambda b0, b1, b2, b3, b4, b5, b6, b7: b7)),
]


# ----------------------------------------------------------------------------
# Bytes, as a homogeneous list of Byte

@combinator
def bytes_test(xs):
    return unit_type(
        app(xs, ok, lambda h, t: unit_and(byte_test(h), bytes_test(t))))
