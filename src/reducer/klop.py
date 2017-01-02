"""Eager linear reduction of linear Bohm term graphs.

This library intends to generalize reducer.bohm operations to reducer.graph
data structures.

"""

from pomagma.compiler.util import MEMOIZED_CACHES, memoize_arg, memoize_args
from pomagma.reducer.graphs import (ABS, APP, BOT, IVAR, JOIN, TOP,
                                    extract_subterm, free_vars, graph_join,
                                    is_abs, is_app, is_graph, is_ivar, is_join,
                                    is_nvar, iter_join)
from pomagma.util import TODO, UnreachableError


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
    elif is_nvar(fun):
        return APP(fun, arg)
    elif is_ivar(fun):
        return APP(fun, arg)
    elif is_abs(fun):
        body = extract_subterm(fun, fun[0][1])
        return substitute(body, arg, 0, False)
    elif is_app(fun):
        return APP(fun, arg)
    elif is_join(fun):
        TODO('extract subterms; make apps; and construct a join')
    else:
        raise ValueError(fun)
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
        return graph_join(frozenset(abstract(g) for g in iter_join(graph)))
    else:
        return ABS(graph)
    raise UnreachableError(graph)


# ----------------------------------------------------------------------------
# Scott ordering

JOIN_CACHE = {}


# Memoized manually.
def join(args):
    # Memoize.
    args = frozenset(args)
    try:
        return JOIN_CACHE[args]
    except KeyError:
        pass

    # Handle trivial cases.
    if not args:
        return BOT
    if TOP in args:
        return TOP
    if len(args) == 1:
        return next(iter(args))

    # Filter out strictly dominated terms (requires transitivity).
    filtered = [
        graph for graph in args
        if not any(dominates(ub, graph) for ub in args if ub is not graph)
    ]

    # Construct a join term.
    return JOIN(filtered)


MEMOIZED_CACHES[join] = JOIN_CACHE


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
