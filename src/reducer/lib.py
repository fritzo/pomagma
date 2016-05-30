"""Standard library of combinators.

Intro forms are hand-optimized; see lib_test.py for lambda versions.

"""

from pomagma.reducer.code import I, K, B, C, TOP, BOT, APP
from pomagma.reducer.sugar import app, untyped, symmetric

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


@untyped
def unit_test(x, f):
    return app(x, f)


# ----------------------------------------------------------------------------
# Bool

true = K
false = APP(K, I)


@untyped
def bool_test(x, f):
    return app(x, f, f)


@untyped
def bool_not(x):
    return app(x, false, true)


@untyped
def bool_and(x, y):
    return app(x, y, false)


@untyped
@symmetric
def bool_or(x, y):
    return app(x, true, y)


# ----------------------------------------------------------------------------
# Maybe

none = K


@untyped
def some(arg):
    return APP(K, APP(CI, arg))


@untyped
def maybe_test(x, f):
    return app(x, f, lambda y: f)


# ----------------------------------------------------------------------------
# Products

@untyped
def pair(x, y):
    return APP(APP(C, APP(CI, x)), y)


@untyped
def prod_test(xy, f):
    return app(xy, lambda x, y: f)


@untyped
def prod_fst(xy):
    return app(xy, lambda x, y: x)


@untyped
def prod_snd(xy):
    return app(xy, lambda x, y: y)


# ----------------------------------------------------------------------------
# Sums

@untyped
def inl(x):
    return COMP(K, APP(CI, x))


@untyped
def inr(y):
    return APP(K, APP(CI, y))


@untyped
def sum_test(xy, f):
    return app(xy, lambda x: f, lambda y: f)


# ----------------------------------------------------------------------------
# Numerals as Y Maybe

zero = none
succ = some


@untyped
def num_test(x, f):
    return app(x, f, lambda px: num_test(px, f))


@untyped
def num_is_zero(x):
    return app(x, true, lambda px: false)


@untyped
def num_pred(x):
    return app(x, error, lambda px: px)


@untyped
@symmetric
def num_add(x, y):
    return app(y, x, lambda py: succ(num_add(x, py)))


@untyped
def num_less(x, y):
    return app(y, false, lambda py: app(x, true, lambda px: num_less(px, py)))


@untyped
def num_rec(z, s, x):
    return app(x, z, lambda px: app(s, num_rec(z, s, px)))


# ----------------------------------------------------------------------------
# Finite homogeneous lists

nil = K


@untyped
def cons(head, tail):
    return APP(K, APP(APP(C, APP(CI, head)), tail))


@untyped
def list_test(xs, f):
    return app(xs, f, lambda h, t: list_test(t, f))


@untyped
def list_empty(xs):
    return app(xs, true, lambda h, t: false)


@untyped
def list_all(xs):
    return app(xs, true, lambda h, t: bool_and(h, list_all(t)))


@untyped
def list_map(f, xs):
    return app(xs, nil, lambda h, t: cons(f(h), list_map(f, t)))


@untyped
def list_rec(n, c, xs):
    return app(xs, n, lambda h, t: app(c, h, list_rec(n, c, t)))
