"""Combinatory logic, a la Haskell Curry."""

from pomagma.compiler.util import memoize_arg, memoize_args
from pomagma.reducer import syntax
from pomagma.reducer.bohm import decrement_rank
from pomagma.reducer.syntax import (APP, BOT, IVAR, JOIN, TOP, B, C, I, K, S,
                                    anonymize, isa_app, isa_atom, isa_join,
                                    isa_nvar)
from pomagma.util import TODO

SUPPORTED_TESTDATA = ['sk']

# ----------------------------------------------------------------------------
# Abstraction

IVAR_0 = IVAR(0)


@memoize_args
def _try_abstract(body):
    """Returns abstraction if IVAR(0) occurs in body, else None."""
    if body is IVAR_0:
        return I  # Rule I
    elif isa_app(body):
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
    elif isa_join(body):
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


# ----------------------------------------------------------------------------
# Computation

@memoize_arg
def try_compute_step(code):
    if isa_atom(code) or isa_nvar(code):
        return None
    elif isa_app(code):
        c1 = code[1]
        c2 = code[2]
        if c1 is TOP:
            return TOP
        elif c1 is BOT:
            return BOT
        elif c1 is I:
            return c2
        elif isa_app(c1):
            c11 = c1[1]
            c12 = c1[2]
            if c11 is K:
                return c12
            elif isa_app(c11):
                c111 = c11[1]
                c112 = c11[2]
                if c111 is B:
                    return APP(c112, APP(c12, c2))
                elif c111 is C:
                    return APP(APP(c112, c2), c12)
                elif c111 is S:
                    return APP(APP(c112, c2), APP(c12, c2))
        c1_step = try_compute_step(c1)
        if c1_step is not None:
            return APP(c1_step, c2)
        c2_step = try_compute_step(c2)
        if c2_step is not None:
            return APP(c1, c2_step)
        return None
    else:
        raise ValueError(code)


def reduce(code, budget=100):
    """Beta-reduce code up to budget."""
    code = convert(code)
    for _ in xrange(budget):
        reduced = try_compute_step(code)
        if reduced is None:
            break
        code = reduced
    return code
