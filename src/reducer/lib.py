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

void = I


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


def num_test(x, f):
    return app(x, f, lambda px: app(num_test, px, f))


num_test = untyped(num_test)


@untyped
def num_is_zero(x):
    return app(x, true, lambda px: false)


@untyped
def num_pred(x):
    return app(x, error, lambda px: px)


@symmetric
def num_add(x, y):
    return app(y, x, lambda py: succ(app(num_add, x, py)))


num_add = untyped(num_add)


# ----------------------------------------------------------------------------
# Finite homogeneous lists

nil = K


@untyped
def cons(head, tail):
    return APP(K, APP(APP(C, APP(CI, head)), tail))


@untyped
def list_is_empty(xs):
    return app(xs, true, lambda h, t: false)
