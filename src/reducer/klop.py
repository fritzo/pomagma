"""Eager linear reduction of linear Bohm term graphs.

This library intends to generalize reducer.bohm operations to reducer.graph
data structures.

"""

from pomagma.compiler.util import memoize_arg, memoize_args, memoize_frozenset
from pomagma.reducer import syntax
from pomagma.reducer.graphs import (ABS, APP, BOT, IVAR, JOIN, NVAR, TOP,
                                    extract_subterm, free_vars, is_abs, is_app,
                                    is_graph, is_join, iter_join)
from pomagma.reducer.util import UnreachableError
from pomagma.util import TODO

I = ABS(IVAR(0))
K = ABS(ABS(IVAR(1)))
B = ABS(ABS(ABS(APP(IVAR(2), APP(IVAR(1), IVAR(0))))))
C = ABS(ABS(ABS(APP(APP(IVAR(2), IVAR(0)), IVAR(1)))))
S = ABS(ABS(ABS(APP(APP(IVAR(2), IVAR(0)), APP(IVAR(1), IVAR(0))))))

KI = ABS(ABS(IVAR(0)))
CB = ABS(ABS(ABS(APP(IVAR(1), APP(IVAR(2), IVAR(0))))))
CI = ABS(ABS(APP(IVAR(0), IVAR(1))))

true = K
false = KI


# ----------------------------------------------------------------------------
# Functional programming

@memoize_arg
def decrement_rank(graph):
    TODO()


@memoize_args
def substitute(graph, value, rank, budget):
    """Substitute value for IVAR(rank) in code, decremeting higher IVARs.

    This is linear-eager, and will be lazy about nonlinear
    substitutions.

    """
    assert budget in (True, False), budget
    TODO()


@memoize_args
def app(fun, arg):
    """Apply function to argument and linearly reduce."""
    if fun is TOP:
        return TOP
    elif fun is BOT:
        return BOT
    elif is_abs(fun):
        body = extract_subterm(fun, fun[0][1])
        return substitute(body, arg, 0, False)
    elif is_join(fun):
        return join(app(g, arg) for g in iter_join(fun))
    else:
        return APP(fun, arg)
    raise UnreachableError((fun, arg))


@memoize_args
def abstract(graph):
    """Abstract one de Bruijn variable and simplify."""
    root = graph[0]
    if graph is TOP:
        return TOP
    elif graph is BOT:
        return BOT
    elif is_app(graph):
        fun = extract_subterm(graph, root[1])
        arg = extract_subterm(graph, root[2])
        if IVAR(0) not in free_vars(fun) and arg is IVAR(0):
            # Eta contract.
            return decrement_rank(fun)
        return ABS(graph)
    elif is_join(graph):
        return join(abstract(g) for g in iter_join(graph))
    else:
        return ABS(graph)
    raise UnreachableError(graph)


# ----------------------------------------------------------------------------
# Scott ordering

@memoize_frozenset
def join(args):
    # Handle trivial cases.
    if TOP in args:
        return TOP
    if BOT in args:
        args = frozenset(arg for arg in args if arg is not BOT)
    if not args:
        return BOT
    if len(args) == 1:
        return next(iter(args))

    # Filter out strictly dominated terms (requires transitivity).
    filtered = [
        arg for arg in args
        if not any(dominates(ub, arg) for ub in args if ub is not arg)
    ]

    # Construct a join term.
    return JOIN(filtered)


def dominates(lhs, rhs):
    """Weak strict domination relation: lhs =] rhs and lhs [!= rhs."""
    lhs_rhs = try_decide_less(lhs, rhs)
    rhs_lhs = try_decide_less(rhs, lhs)
    return rhs_lhs is True and lhs_rhs is False


@memoize_args
def try_decide_less(lhs, rhs):
    """Weak decision procedure returning True, False, or None."""
    assert is_graph(lhs), lhs
    assert is_graph(rhs), rhs

    # Try simple cases.
    if lhs is BOT or lhs is rhs or rhs is TOP:
        return True
    if lhs is TOP and rhs is BOT:
        return False

    # TODO Try harder.

    # Give up.
    return None


# ----------------------------------------------------------------------------
# Conversion

SIGNATURE = {
    'NVAR': NVAR,
    'IVAR': IVAR,
    'APP': app,
    'JOIN': join,
    'ABS': abstract,
    'I': I,
    'K': K,
    'B': B,
    'C': C,
    'S': S,
}

convert = syntax.Transform(**SIGNATURE)
