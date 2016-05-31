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
def bool_and(x, y):
    return app(x, y, false)


@combinator
@symmetric
def bool_or(x, y):
    return app(x, true, y)


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
