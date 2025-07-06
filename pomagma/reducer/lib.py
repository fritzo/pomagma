"""
Standard library of combinators.

Objects in this library are either `Term`s or `_Combinator`s that can be
converted to terms via `pomagma.reducer.sugar.as_term()`.

Intro forms are hand-optimized; see `lib_test.py` for lambda versions.
"""

from pomagma.reducer.bohm import CI, KI, B, C, I, K, false, true
from pomagma.reducer.sugar import (
    app,
    combinator,
    join_,
    let,
    qapp,
    quote,
    symmetric,
    typed,
)
from pomagma.reducer.syntax import (
    BOOL,
    BOT,
    EVAL,
    MAYBE,
    NUM,
    QEQUAL,
    QLESS,
    QUOTE,
    SEMI,
    TOP,
    UNIT,
)

################################################################
# Nondeterminism

join = K | KI
_ = BOT


################################################################
# Errors

error = TOP
undefined = BOT


################################################################
# Semi-boolean type with inhabitants {BOT, I, TOP}

ok = I


@combinator
def semi_type(x):
    return SEMI(x)


@combinator
def semi_test(x):
    return semi_type(x)


@combinator
@typed(semi_type, semi_type, semi_type)
@symmetric
def semi_meet(x, y):
    return x(y)


@combinator
@typed(semi_type, semi_type, semi_type)
@symmetric
def semi_join(x, y):
    return x | y


@combinator
def semi_quote(x):
    x = semi_type(x)
    return x(QUOTE(ok))


enum_semi = CI(ok)


################################################################
# Unit type with inhabitants {I, TOP}


@combinator
def unit_type(x):
    return UNIT(x)


@combinator
def unit_test(x):
    return unit_type(x)


@combinator
@typed(unit_type, unit_type, unit_type)
@symmetric
def unit_and(x, y):
    return x(y)


@combinator
@typed(unit_type, unit_type, unit_type)
def unit_or(x, y):
    return x | y


@combinator
def unit_quote(x):
    x = unit_type(x)
    return x(QUOTE(ok))


enum_unit = CI(ok)


################################################################
# Boolean type with inhabitants {BOT, K, KI, TOP}

assert true is K
assert false is KI


@combinator
def bool_type(x):
    return BOOL(x)


@combinator
@typed(bool_type, semi_type)
def bool_test(x):
    return x(ok, ok)


@combinator
@typed(bool_type, bool_type)
def bool_not(x):
    return x(false, true)


@combinator
@typed(bool_type, bool_type, bool_type)
@symmetric
def bool_and(x, y):
    return x(y, false)


@combinator
@typed(bool_type, bool_type, bool_type)
@symmetric
def bool_or(x, y):
    return x(true, y)


@combinator
def bool_quote(x):
    x = bool_type(x)
    return x(QUOTE(true), QUOTE(false))


@combinator
def bool_if_true(x):
    x = bool_type(x)
    return semi_type(x(ok, _))


@combinator
def bool_if_false(x):
    x = bool_type(x)
    return semi_type(x(_, ok))


enum_bool = CI(true) | CI(false)


################################################################
# Maybe type with inhabitants {BOT, none, TOP} u {some(x) | x}

none = K


@combinator
def some(arg):
    return K(CI(arg))


@combinator
def maybe_type(x):
    return MAYBE(x)


@combinator
def maybe_test(x):
    x = maybe_type(x)
    return semi_type(x(ok, lambda y: ok))


@combinator
def maybe_quote(quote_some, x):
    x = maybe_type(x)
    return x(QUOTE(none), lambda y: qapp(quote(some), quote_some(y)))


@combinator
def enum_maybe(enum_item):
    return box(none) | enum_map(some, enum_item)


################################################################
# Products with inhabitants {TOP} u {pair(x, y) | x, y}


@combinator
def pair(x, y):
    return C(CI(x), y)


@combinator
def prod_test(xy):
    return semi_type(xy(lambda x, y: ok))


@combinator
def prod_fst(xy):
    return xy(lambda x, y: x)


@combinator
def prod_snd(xy):
    return xy(lambda x, y: y)


@combinator
def prod_quote(quote_fst, quote_snd, xy):
    return xy(lambda x, y: qapp(quote(pair), quote_fst(x), quote_snd(y)))


@combinator
def enum_prod(enum_fst, enum_snd):
    return enum_fst(lambda x: enum_snd(lambda y: box(pair(x, y))))


################################################################
# Sums with inhabitants {BOT, TOP} u {inl(x) | x} u {inr(y) | y}


@combinator
def inl(x):
    return B(K, CI(x))


@combinator
def inr(y):
    return K(CI(y))


@combinator
def sum_test(xy):
    return semi_type(xy(lambda x: ok, lambda y: ok))


@combinator
def sum_quote(quote_inl, quote_inr, xy):
    return xy(
        lambda x: qapp(quote(inl), quote_inl(x)),
        lambda y: qapp(quote(inr), quote_inr(y)),
    )


@combinator
def enum_sum(enum_inl, enum_inr):
    return enum_map(inl, enum_inl) | enum_map(inr, enum_inr)


################################################################
# Numerals as Y Maybe

zero = none
succ = some


@combinator
def num_type(x):
    return NUM(x)


@combinator
@typed(num_type, semi_type)
def num_test(x):
    return semi_type(x(ok, num_test))


@combinator
@typed(num_type, bool_type)
def num_is_zero(x):
    return x(true, lambda px: false)


@combinator
@typed(num_type, num_type)
def num_pred(x):
    return x(error, lambda px: px)


@combinator
@typed(num_type, num_type, num_type)
@symmetric
def num_add(x, y):
    return y(x, lambda py: succ(num_add(x, py)))


@combinator
@typed(num_type, num_type, num_type)
@symmetric
def num_mul(x, y):
    return num_rec(zero, lambda py: num_add(x, py), y)


@combinator
@typed(num_type, num_type, semi_type)
@symmetric
def num_if_eq(x, y):
    return x(y(ok, _), lambda px: y(_, lambda py: num_if_eq(px, py)))


@combinator
@typed(num_type, num_type, bool_type)
@symmetric
def num_eq(x, y):
    return x(y(true, lambda py: false), lambda px: y(false, lambda py: num_eq(px, py)))


@combinator
@typed(num_type, num_type, semi_type)
def num_if_le(x, y):
    return x(y(ok, lambda _: ok), lambda px: y(_, lambda py: num_if_le(px, py)))


@combinator
@typed(num_type, num_type, bool_type)
def num_le(x, y):
    return x(true, lambda px: y(false, lambda py: num_le(px, py)))


@combinator
@typed(num_type, num_type, bool_type)
def num_lt(x, y):
    return y(false, lambda py: x(true, lambda px: num_lt(px, py)))


@combinator
# @typed ???
def num_rec(z, s, x):
    return x(z, lambda px: s(num_rec(z, s, px)))


@combinator
def num_quote(x):
    return x(QUOTE(zero), lambda px: qapp(quote(succ), num_quote(px)))


@combinator
def enum_num():
    return box(zero) | enum_map(succ, enum_num)


################################################################
# Finite homogeneous lists

nil = K


@combinator
def cons(head, tail):
    return K(C(CI(head), tail))


@combinator
def list_test(xs):
    return semi_type(xs(ok, lambda h, t: list_test(t)))


@combinator
def list_empty(xs):
    return xs(true, lambda h, t: false)


@combinator
def list_all(xs):
    return xs(true, lambda h, t: bool_and(h, list_all(t)))


@combinator
def list_any(xs):
    return xs(false, lambda h, t: bool_or(h, list_any(t)))


@combinator
def list_cat(xs, ys):
    return xs(ys, lambda h, t: cons(h, list_cat(t, ys)))


@combinator
def list_map(f, xs):
    return xs(nil, lambda h, t: cons(f(h), list_map(f, t)))


@combinator
def list_rec(n, c, xs):
    return xs(n, lambda h, t: c(h, list_rec(n, c, t)))


@combinator
def list_filter(p, xs):
    p = compose(bool_type, p)
    return list_rec(nil, lambda h, t: p(h, app(cons, h), I, t), xs)


@combinator
def list_size(xs):
    return xs(zero, lambda h, t: succ(list_size(t)))


@combinator
def list_sort(lt, xs):
    return let(
        list_sort(lt),
        lambda sort: xs(
            nil,
            lambda h, t: let(
                lt(h),
                lambda lt_h: list_cat(
                    sort(list_filter(lt_h, t)),
                    cons(h, sort(list_filter(compose(bool_not, lt_h), t))),
                ),
            ),
        ),
    )


@combinator
def list_quote(quote_item, xs):
    return xs(QUOTE(nil), lambda h, t: qapp(quote(cons), quote_item(h), list_quote(t)))


@combinator
def enum_list(enum_item):
    return box(nil) | enum_list(
        enum_item, lambda t: enum_item(lambda h: box(cons(h, t)))
    )


################################################################
# Streams


@combinator
def stream_cons(head, tail):
    return lambda f: f(head, tail)


@combinator
def stream_head(xs):
    return xs(lambda h, t: h)


@combinator
def stream_tail(xs):
    return xs(lambda h, t: t)


@combinator
def stream_test(test_item, xs):
    return I | xs(lambda h, t: test_item(h) | stream_test(t))


@combinator
def stream_const(x):
    return stream_cons(x, stream_const(x))


stream_bot = stream_const(BOT)


@combinator
def stream_join(xs):
    return xs(lambda h, t: h | stream_join(t))


@combinator
def stream_map(f, xs):
    return xs(lambda h, t: stream_cons(f(h), stream_map(t)))


@combinator
def stream_zip(xs, ys):
    return xs(
        lambda xh, xt: ys(lambda yh, yt: stream_cons(pair(xh, yh), stream_zip(xt, yt)))
    )


@combinator
def stream_dovetail(xs, ys):
    return xs(
        lambda xh, xt: stream_cons(
            xh, ys(lambda yh, yt: stream_cons(yh, stream_dovetail(xt, yt)))
        )
    )


@combinator
def stream_quote(quote_item, xs):
    return xs(
        lambda h, t: qapp(
            quote(stream_cons), quote_item(h), stream_quote(quote_item, t)
        )
    )


@combinator
def enum_stream(enum_item):
    return enum_item(
        lambda h: stream_cons(h, stream_bot)
        | enum_stream(enum_item, lambda t: stream_cons(h, t))
    )


@combinator
def stream_num():
    return stream_cons(zero, stream_map(succ, stream_num))


@combinator
def stream_take(xs, size):
    """Return a list containing the first `size` elements of a stream."""
    return size(nil, lambda p: xs(lambda h, t: cons(h, stream_take(t, p))))


################################################################
# Enumerable sets


@combinator
def box(item):
    return CI(item)


def enum(items):
    assert isinstance(items, list | set | frozenset), items
    return join_(*list(map(box, items)))


@combinator
def enum_test(xs):
    return semi_type(xs(lambda x: ok))


@combinator
def enum_union(xs, ys):
    return xs | ys


@combinator
def enum_any(xs):
    return semi_type(xs(semi_type))


@combinator
def enum_filter(p, xs):
    p = compose(semi_type, p)
    return xs(lambda x: p(x, box(x)))


@combinator
def enum_map(f, xs):
    return xs(lambda x: box(f(x)))


@combinator
def enum_flatten(xs):
    return xs(lambda x: x)


@combinator
def enum_close(f, xs):
    """forall a, (a -> enum a) -> enum a -> enum a."""
    # return close(lambda ys: ys(f), xs)
    return enum_union(xs, enum_close(f, xs, f))


################################################################
# Functions


@combinator
def compose(f, g):
    return lambda x: f(g(x))


@combinator
def fun_type(domain_type, codomain_type):
    return lambda f, x: codomain_type(f(domain_type(x)))


@combinator
def fix(f):
    """The Y combinator."""
    return app(f, fix(f))


@combinator
def qfix(qf):
    return EVAL(qf, qapp(quote(qfix), qf))


@combinator
def close(f):
    """Scott's universal closure operator V."""
    return lambda x: x | f(close(x))


################################################################
# Type constructor


@combinator
def a_preconj(f):
    return f(lambda r, s: pair(B(r), B(s)))


@combinator
def a_postconj(f):
    return f(lambda r, s: pair(C(B, s), C(B, r)))


@combinator
def a_compose(f1, f2):
    return f1(lambda r1, s1: f2(lambda r2, s2: pair(B(r1, r2), B(s2, s1))))


@combinator
def div(f):
    return f | div(f, TOP)


@combinator
def a_copy(f, x):
    return f(x, x)


@combinator
def a_join(f, x, y):
    return f(x | y)


@combinator
def a_construct():
    return join_(
        pair(I, I),
        pair(BOT, TOP),
        pair(div, BOT),
        pair(a_copy, a_join),
        pair(C, C),
        a_preconj(a_construct),
        a_postconj(a_construct),
        a_compose(a_construct, a_construct),
    )


@combinator
def construct(f):
    """The simple type constructor, aka AAA."""
    return app(a_construct, f)


@construct
def a_arrow(a, b):
    return lambda f, x: b(f(a(x)))


################################################################
# Scott ordering


@combinator
def equal(x, y):
    return bool_type(QEQUAL(x, y))


@combinator
def less(x, y):
    return bool_type(QLESS(x, y))


@combinator
def enum_contains(qxs, qy):
    return QLESS(qapp(quote(box), qy), qxs)


################################################################
# Byte as an 8-tuple of bits


def _make_bits_table(n):
    table = {0: I}
    for i in range(n):
        prev = table
        table = {}
        for k, v in list(prev.items()):
            table[k] = C(v, false)
            table[k | (1 << i)] = C(v, true)
    return table


byte_table = _make_bits_table(8)
assert len(byte_table) == 256


def _bits_test(b0, b1, b2, b3, b4, b5, b6, b7):
    bits = [b0, b1, b2, b3, b4, b5, b6, b7]
    tests = list(map(bool_test, bits))
    all_defined = app(*tests)
    any_error = join_(*tests)
    return any_error(all_defined)


@combinator
def byte_test(x):
    return semi_type(x(_bits_test))


@combinator
def byte_make(b0, b1, b2, b3, b4, b5, b6, b7):
    result = I
    for b in (b0, b1, b2, b3, b4, b5, b6, b7):
        result = C(result, b)
    return result


byte_get_bit = [
    combinator(lambda x: x(lambda b0, b1, b2, b3, b4, b5, b6, b7: b0)),
    combinator(lambda x: x(lambda b0, b1, b2, b3, b4, b5, b6, b7: b1)),
    combinator(lambda x: x(lambda b0, b1, b2, b3, b4, b5, b6, b7: b2)),
    combinator(lambda x: x(lambda b0, b1, b2, b3, b4, b5, b6, b7: b3)),
    combinator(lambda x: x(lambda b0, b1, b2, b3, b4, b5, b6, b7: b4)),
    combinator(lambda x: x(lambda b0, b1, b2, b3, b4, b5, b6, b7: b5)),
    combinator(lambda x: x(lambda b0, b1, b2, b3, b4, b5, b6, b7: b6)),
    combinator(lambda x: x(lambda b0, b1, b2, b3, b4, b5, b6, b7: b7)),
]


################################################################
# Bytes, as a homogeneous list of Byte


@combinator
def bytes_test(xs):
    return semi_type(xs(ok, lambda h, t: unit_and(byte_test(h), bytes_test(t))))
