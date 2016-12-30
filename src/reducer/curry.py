"""Conversions to combinatory logic, a la Curry."""

from pomagma.compiler.util import memoize_args
from pomagma.reducer import syntax
from pomagma.reducer.bohm import decrement_rank
from pomagma.reducer.syntax import (APP, BOT, IVAR, JOIN, TOP, B, C, I, K, S,
                                    anonymize, is_app, is_join)
from pomagma.util import TODO

# ----------------------------------------------------------------------------
# Abstraction

IVAR_0 = IVAR(0)


@memoize_args
def _try_abstract(body):
    """Returns abstraction if IVAR(0) occurs in body, else None."""
    if body is IVAR_0:
        return I  # Rule I
    elif is_app(body):
        lhs = body[1]
        rhs = body[2]
        lhs_abs = _try_abstract(lhs)
        rhs_abs = _try_abstract(rhs)
        if lhs_abs is None:
            if rhs_abs is None:
                return None  # Rule K
            elif rhs_abs is I:
                return decrement_rank(lhs)  # Rule eta
            else:
                return APP(APP(B, decrement_rank(lhs)), rhs_abs)  # Rule B
        else:
            if rhs_abs is None:
                return APP(APP(C, lhs_abs), decrement_rank(rhs))  # Rule C
            else:
                return APP(APP(S, lhs_abs), rhs_abs)  # Rule S
    elif is_join(body):
        lhs = body[1]
        rhs = body[2]
        lhs_abs = _try_abstract(lhs)
        rhs_abs = _try_abstract(rhs)
        if lhs_abs is None:
            if rhs_abs is None:
                return None  # Rule K
            else:
                # Rule JOIN-K
                return JOIN(APP(K, decrement_rank(lhs)), rhs_abs)
        else:
            if rhs_abs is None:
                # Rule JOIN-K
                return JOIN(lhs_abs, APP(K, decrement_rank(rhs)))
            else:
                return JOIN(lhs_abs, rhs_abs)  # Rule JOIN
    else:
        return None  # Rule K


def de_bruijn_abstract(body):
    """APP,JOIN,TOP,BOT,I,K,B,C,S,eta-abstraction algorithm."""
    result = _try_abstract(body)
    if result is not None:
        return result
    elif body in (TOP, BOT):
        return body  # Rules TOP, BOT
    else:
        return APP(K, decrement_rank(body))  # Rule K


def abstract(var, body):
    """APP,JOIN,TOP,BOT,I,K,B,C,S,eta-abstraction algorithm."""
    return de_bruijn_abstract(anonymize(body, var, convert))


def qabstract(var, body):
    TODO('Support quoted recursion')


# ----------------------------------------------------------------------------
# Symbolic compiler : ABS,FUN -> I,K,B,C,S

convert = syntax.Transform(FUN=abstract, ABS=de_bruijn_abstract)
