"""Rational Term Graphs.

Graphs are represented as tuples of function symbols applied to vertex ids,
where the 0th location of the tuple is the root.

"""

import itertools
import re

from pomagma.compiler.util import memoize_arg, memoize_args, unique

re_keyword = re.compile('[A-Z]+$')

GRAPHS = {}  # : graph -> graph

_TOP = intern('TOP')
_BOT = intern('BOT')
_NVAR = intern('NVAR')
_IVAR = intern('IVAR')
_ABS = intern('ABS')
_APP = intern('APP')
_JOIN = intern('JOIN')


def term_make(*args):
    return unique(args)


def term_join(lhs, rhs):
    assert lhs != rhs
    if lhs < rhs:
        return term_make(_JOIN, lhs, rhs)
    else:
        return term_make(_JOIN, rhs, lhs)


def term_shift(term, delta):
    symbol = term[0]
    if symbol in (_TOP, _BOT, _NVAR, _IVAR):
        return term
    elif symbol is _ABS:
        return term_make(_ABS, term[1] + delta)
    elif symbol is _APP:
        return term_make(_APP, term[1] + delta, term[2] + delta)
    elif symbol is _JOIN:
        return term_join(term[1] + delta, term[2] + delta)
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
        return term_join(perm[term[1]], perm[term[2]])
    else:
        raise ValueError(term)


def graph_deduplicate(terms):
    # TODO Deduplicate variables.
    return terms


def perm_inverse(perm):
    result = [None] * len(perm)
    for i, j in enumerate(perm):
        result[j] = i
    return result


def graph_permute(graph, perm):
    return tuple(term_permute(graph[i], perm) for i in perm_inverse(perm))


def graph_sort(graph):
    # FIXME This is very slow.
    return min(
        graph_permute(graph, (0,) + p)
        for p in itertools.permutations(range(1, len(graph)))
    )


def graph_make(terms):
    terms = graph_deduplicate(terms)
    graph = graph_sort(terms)
    return GRAPHS.setdefault(graph, graph)


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
    body_pos = 1
    terms = [term_make(_ABS, body_pos)]
    for term in body:
        terms.append(term_shift(term, body_pos))
    return graph_make(terms)


@memoize_args
def APP(lhs, rhs):
    lhs_pos = 1
    rhs_pos = 1 + len(lhs)
    terms = [term_make(_APP, lhs_pos, rhs_pos)]
    for term in lhs:
        terms.append(term_shift(term, lhs_pos))
    for term in rhs:
        terms.append(term_shift(term, rhs_pos))
    return graph_make(terms)


@memoize_args
def JOIN(lhs, rhs):
    if lhs is rhs:
        return lhs
    lhs_pos = 1
    rhs_pos = 1 + len(lhs)
    terms = [term_make(_JOIN, lhs_pos, rhs_pos)]
    for term in lhs:
        terms.append(term_shift(term, lhs_pos))
    for term in rhs:
        terms.append(term_shift(term, rhs_pos))
    return graph_make(terms)
