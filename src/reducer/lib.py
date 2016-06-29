"""Standard library of combinators.

Intro forms are hand-optimized; see lib_test.py for lambda versions.

"""

from pomagma.reducer.code import I, K, B, C, TOP, BOT, APP
from pomagma.reducer.sugar import app, join, combinator, symmetric

CI = APP(C, I)


def COMP(lhs, rhs):
    return APP(APP(B, lhs), rhs)


# ----------------------------------------------------------------------------
# Errors

error = TOP
undefined = BOT


# ----------------------------------------------------------------------------
# Unit

ok = I


@combinator
def unit_test(x):
    return app(x, ok)


@combinator
@symmetric
def unit_and(x, y):
    return app(x, y)


@combinator
def unit_or(x, y):
    return join(x, y)


# ----------------------------------------------------------------------------
# Bool

true = K
false = APP(K, I)


@combinator
def bool_test(x):
    return app(x, ok, ok)


@combinator
def bool_not(x):
    return app(x, false, true)


@combinator
@symmetric
def bool_and(x, y):
    return app(x, y, false)


@combinator
@symmetric
def bool_or(x, y):
    return app(x, true, y)


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
    return app(join(*tests), *tests)


@combinator
def byte_test(x):
    return app(x, _bits_test)


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
# Maybe

none = K


@combinator
def some(arg):
    return APP(K, APP(CI, arg))


@combinator
def maybe_test(x):
    return app(x, ok, lambda y: ok)


# ----------------------------------------------------------------------------
# Products

@combinator
def pair(x, y):
    return APP(APP(C, APP(CI, x)), y)


@combinator
def prod_test(xy):
    return app(xy, lambda x, y: ok)


@combinator
def prod_fst(xy):
    return app(xy, lambda x, y: x)


@combinator
def prod_snd(xy):
    return app(xy, lambda x, y: y)


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
    return app(xy, lambda x: ok, lambda y: ok)


# ----------------------------------------------------------------------------
# Numerals as Y Maybe

zero = none
succ = some


@combinator
def num_test(x):
    return app(x, ok, num_test)


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
def num_eq(x, y):
    return app(x, app(y, true, lambda py: false), lambda px:
               app(y, false, lambda py: num_eq(px, py)))


@combinator
def num_less(x, y):
    return app(y, false, lambda py: app(x, true, lambda px: num_less(px, py)))


@combinator
def num_rec(z, s, x):
    return app(x, z, lambda px: app(s, num_rec(z, s, px)))


# ----------------------------------------------------------------------------
# Finite homogeneous lists

nil = K


@combinator
def cons(head, tail):
    return APP(K, APP(APP(C, APP(CI, head)), tail))


@combinator
def list_test(xs):
    return app(xs, ok, lambda h, t: list_test(t))


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
def list_map(f, xs):
    return app(xs, nil, lambda h, t: cons(app(f, h), list_map(f, t)))


@combinator
def list_rec(n, c, xs):
    return app(xs, n, lambda h, t: app(c, h, list_rec(n, c, t)))


# ----------------------------------------------------------------------------
# Bytes, as a homogeneous list of Byte

@combinator
def bytes_test(xs):
    return app(xs, ok, lambda h, t: unit_and(byte_test(h), bytes_test(t)))
