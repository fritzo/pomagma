"""Rational Term Graphs.

Graphs are represented as tuples of function symbols applied to vertex ids,
where the 0th location of the tuple is the root.

This rooted graph data structure intends to represent terms just coarsely
enough to enable cons hashing modulo isomorphism of rooted graphs. In
particular, we choose fintary JOIN over binary JOIN so as to ease the
isomorphism problem.

"""

import itertools
import re

from pomagma.compiler.util import (MEMOIZED_CACHES, memoize_arg, memoize_args,
                                   unique)
from pomagma.util import TODO

re_keyword = re.compile('[A-Z]+$')

GRAPHS = {}  # : graph -> graph

_TOP = intern('TOP')  # : term
_BOT = intern('BOT')  # : term
_NVAR = intern('NVAR')  # : string -> term
_IVAR = intern('IVAR')  # : int -> term
_ABS = intern('ABS')  # : term -> term
_APP = intern('APP')  # : term -> term -> term
_JOIN = intern('JOIN')  # : frozenset term -> term


def term_make(*args):
    return unique(args)


def term_join(args):
    return term_make(_JOIN, unique(frozenset(args)))


def term_shift(term, delta):
    symbol = term[0]
    if symbol in (_TOP, _BOT, _NVAR, _IVAR):
        return term
    elif symbol is _ABS:
        return term_make(_ABS, term[1] + delta)
    elif symbol is _APP:
        return term_make(_APP, term[1] + delta, term[2] + delta)
    elif symbol is _JOIN:
        return term_join(i + delta for i in term[1])
    else:
        raise ValueError(term)


def term_permute(term, perm):
    symbol = term[0]
    if symbol in (_TOP, _BOT, _NVAR, _IVAR):
        return term
    elif symbol is _ABS:
        return term_make(_ABS, perm[term[1]])
    elif symbol is _APP:
        return term_make(_APP, perm[term[1]], perm[term[2]])
    elif symbol is _JOIN:
        return term_join(perm[i] for i in term[1])
    else:
        raise ValueError(term)


def graph_simplify(terms):
    """Remove unused vertices and deduplicate equivalent vertices."""
    # TODO
    return terms


def perm_inverse(perm):
    result = [None] * len(perm)
    for i, j in enumerate(perm):
        result[j] = i
    return result


def graph_permute(graph, perm):
    return tuple(term_permute(graph[i], perm) for i in perm_inverse(perm))


def graph_sort(graph):
    """Canonicalize the ordering of vertices in a graph."""
    # FIXME This is very slow.
    # TODO Speed this up by first partitioning by symbol, then greedily sorting
    # each partition while adding constraints to later partitions.
    return min(
        graph_permute(graph, (0,) + p)
        for p in itertools.permutations(range(1, len(graph)))
    )


def graph_make(terms):
    """Make a canonical graph, given a messy list of terms."""
    terms = graph_simplify(terms)
    graph = graph_sort(terms)
    return GRAPHS.setdefault(graph, graph)


@memoize_args
def extract_subterm(graph, pos):
    """Extract the subterm of a graph at given root position."""
    assert isinstance(pos, int) and 0 <= pos and pos < len(graph), pos
    perm = range(len(graph))
    perm[0] = pos
    perm[pos] = 0
    terms = graph_permute(graph, perm)
    return graph_make(terms)


TOP = graph_make([term_make(_TOP)])
BOT = graph_make([term_make(_BOT)])


@memoize_arg
def NVAR(name):
    if re_keyword.match(name):
        raise ValueError('Variable names cannot match [A-Z]+: {}'.format(name))
    terms = [term_make(_NVAR, intern(name))]
    return graph_make(terms)


@memoize_arg
def IVAR(rank):
    if not (isinstance(rank, int) and rank >= 0):
        raise ValueError(
            'Variable index must be a natural number {}'.format(rank))
    terms = [term_make(_IVAR, rank)]
    return graph_make(terms)


@memoize_arg
def ABS(body):
    body_offset = 1
    terms = [term_make(_ABS, body_offset)]
    for term in body:
        terms.append(term_shift(term, body_offset))
    return graph_make(terms)


@memoize_args
def APP(lhs, rhs):
    lhs_offset = 1
    rhs_offset = 1 + len(lhs)
    terms = [term_make(_APP, lhs_offset, rhs_offset)]
    for term in lhs:
        terms.append(term_shift(term, lhs_offset))
    for term in rhs:
        terms.append(term_shift(term, rhs_offset))
    return graph_make(terms)


JOIN_CACHE = {}


# Memoized manually.
def JOIN(args):
    # Memoize.
    args = frozenset(args)
    try:
        return JOIN_CACHE[args]
    except KeyError:
        pass

    # Handle trivial cases.
    if not args:
        return BOT
    elif len(args) == 1:
        return next(iter(args))

    # Construct a join term.
    args = list(args)
    offsets = [1]
    for arg in args[:-1]:
        offsets.append(offsets[-1] + len(arg))
    terms = [term_join(offsets)]
    for arg, offset in itertools.izip(args, offsets):
        for term in arg:
            terms.append(term_shift(term, offset))
    return graph_make(terms)


MEMOIZED_CACHES[JOIN] = JOIN_CACHE


def is_graph(graph):
    return graph in GRAPHS


def is_nvar(graph):
    return graph[0][0] is _NVAR


def is_ivar(graph):
    return graph[0][0] is _IVAR


def is_abs(graph):
    return graph[0][0] is _ABS


def is_app(graph):
    return graph[0][0] is _APP


def is_join(graph):
    return graph[0][0] is _JOIN


@memoize_arg
def free_vars(graph):
    TODO()


def iter_join(graph):
    """Destructs JOIN and BOT terms."""
    symbol = graph[0][0]
    if symbol is _JOIN:
        for pos in graph[0][1]:
            yield extract_subterm(graph, pos)
    elif symbol is not _BOT:
        yield graph
