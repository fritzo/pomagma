from pomagma.reducer.code import I, K, B, C, TOP, BOT, APP
from pomagma.reducer.sugar import untyped

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


# ----------------------------------------------------------------------------
# Bool

true = K
false = APP(K, I)


# ----------------------------------------------------------------------------
# Maybe

none = K


@untyped
def some(arg):
    return APP(K, APP(CI, arg))


# ----------------------------------------------------------------------------
# Products

@untyped
def pair(x, y):
    return APP(APP(C, APP(CI, x)), y)


# ----------------------------------------------------------------------------
# Sums

@untyped
def inl(x):
    return COMP(K, APP(CI, x))


@untyped
def inr(y):
    return APP(K, APP(CI, y))


# ----------------------------------------------------------------------------
# Numerals as Y Maybe

zero = none
succ = some


# ----------------------------------------------------------------------------
# Finite homogeneous lists

nil = K


@untyped
def cons(head, tail):
    return APP(K, APP(APP(C, APP(CI, head)), tail))
