"""Rational Term Graphs.

Graphs are represented as tuples of function symbols applied to vertex ids,
where the 0th location of the tuple is the root.

This rooted graph data structure intends to represent terms just coarsely
enough to enable cons hashing modulo isomorphism of rooted graphs. In
particular, we choose fintary JOIN over binary JOIN so as to ease the
isomorphism problem: JOIN terms are syntactically accociative, commutative, and
idempotent.

"""

import functools
import itertools
import re
from collections import defaultdict, deque

from pomagma.compiler.util import memoize_arg, memoize_args

# ----------------------------------------------------------------------------
# Signature

re_keyword = re.compile('[A-Z]+$')

_TOP = intern('TOP')  # : term
_NVAR = intern('NVAR')  # : string -> term
_VAR = intern('VAR')  # : term -> term
_ABS = intern('ABS')  # : term -> term
_APP = intern('APP')  # : term -> term -> term
_JOIN = intern('JOIN')  # : set term -> term


class Term(tuple):
    def __repr__(self):
        symbol = self[0]
        if symbol is _TOP:
            return 'TOP'
        elif symbol is _NVAR:
            return "NVAR('{}')".format(self[1])
        else:
            args = ','.join(str(a) for a in self[1:])
            return '{}({})'.format(symbol, args)

    __str__ = __repr__

    @staticmethod
    @memoize_args
    def make(*args):
        return Term(args)


Term.TOP = Term.make(_TOP)
Term.NVAR = staticmethod(lambda name: Term.make(_NVAR, name))
Term.VAR = staticmethod(lambda abs_: Term.make(_VAR, abs_))
Term.ABS = staticmethod(lambda body: Term.make(_ABS, body))
Term.APP = staticmethod(lambda lhs, rhs: Term.make(_APP, lhs, rhs))
Term.JOIN = staticmethod(lambda args: Term.make(_JOIN, *sorted(set(args))))


class Graph(tuple):
    @staticmethod
    @memoize_args
    def make(*args):
        return Graph(args)


def term_shift(term, delta):
    assert isinstance(term, Term)
    symbol = term[0]
    if symbol in (_TOP, _NVAR):
        return term
    elif symbol is _VAR:
        return Term.VAR(term[1] + delta)
    elif symbol is _ABS:
        return Term.ABS(term[1] + delta)
    elif symbol is _APP:
        return Term.APP(term[1] + delta, term[2] + delta)
    elif symbol is _JOIN:
        return Term.JOIN(i + delta for i in term[1:])
    else:
        raise ValueError(term)


def term_permute(term, perm):
    assert isinstance(term, Term)
    symbol = term[0]
    if symbol in (_TOP, _NVAR):
        return term
    elif symbol is _VAR:
        return Term.VAR(perm[term[1]])
    elif symbol is _ABS:
        return Term.ABS(perm[term[1]])
    elif symbol is _APP:
        return Term.APP(perm[term[1]], perm[term[2]])
    elif symbol is _JOIN:
        return Term.JOIN(perm[i] for i in term[1:])
    else:
        raise ValueError(term)


def perm_inverse(perm):
    result = [None] * (1 + max(perm))
    for i, j in enumerate(perm):
        if j is not None:
            result[j] = i
    return result


def graph_permute(terms, perm):
    return [
        term_permute(terms[i], perm)
        for i in perm_inverse(perm)
        if i is not None
    ]


_APP_LHS = intern('APP_LHS')
_APP_RHS = intern('APP_RHS')


def term_iter_subterms(term):
    assert isinstance(term, Term)
    symbol = term[0]
    if symbol is _VAR:
        yield _VAR, term[1]
    elif symbol is _ABS:
        yield _ABS, term[1]
    elif symbol is _APP:
        yield _APP_LHS, term[1]
        yield _APP_RHS, term[2]
    elif symbol is _JOIN:
        for part in term[1:]:
            yield _JOIN, part


def graph_prune(terms):
    """Remove vertices unreachable from the root."""
    assert all(isinstance(term, Term) for term in terms)
    connected = set([0])
    pending = [0]
    while pending:
        term = terms[pending.pop()]
        for _, pos in term_iter_subterms(term):
            if pos not in connected:
                connected.add(pos)
                pending.append(pos)
    if len(connected) == len(terms):
        return terms
    perm = perm_inverse(sorted(connected))
    return graph_permute(terms, perm)


def graph_quotient_weak(terms):
    """Deduplicate vertices by forward-chaining equality.

    This cheap incomplete algorithm simply identifies equivalent terms.
    This algorithm cannot deduplicate cyclic terms.
    """
    while True:
        partitions = defaultdict(list)
        for i, term in enumerate(terms):
            partitions[term].append(i)
        if len(partitions) == len(terms):
            break
        partitions = sorted(map(sorted, partitions.values()))
        assert 0 in partitions[0], partitions
        perm = [None] * len(terms)
        for target, sources in enumerate(partitions):
            for source in sources:
                perm[source] = target
        assert all(target is not None for target in perm)
        terms = graph_permute(terms, perm)
    return terms


class ApartnessRelation(object):
    def __init__(self, size):
        self._size = size
        self._table = [False] * (size * size)

    def add(self, x, y):
        assert isinstance(x, int), x
        assert isinstance(y, int), y
        assert x != y
        self._table[x + y * self._size] = True
        self._table[y + x * self._size] = True

    def __call__(self, x, y):
        assert isinstance(x, int), x
        assert isinstance(y, int), y
        return self._table[x + y * self._size]

    def __len__(self):
        return sum(self._table)

    def copy(self):
        other = ApartnessRelation(self._size)
        other._table = self._table[:]
        return other


def graph_quotient_strong(terms):
    """Deduplicate vertices by forward-chaining apartness and backtracking.

    This complete algorithm is similar to the standard algorithm for
    minimization of nondeterministic finite automata. For deterministic terms,
    it suffices to forward-chain apartness (aka separability aka
    distinguishability) and quotient by the resulting equivalence relation.
    However JOIN terms introduce nondeterminism and require additional
    backtracking.
    """
    # Compute apartness by forward-chaining.
    apart = ApartnessRelation(size=len(terms))
    old_count = -1
    while len(apart) > old_count:
        old_count = len(apart)
        for i, x in enumerate(terms):
            symbol = x[0]
            for j, y in enumerate(terms[:i]):
                if y[0] is not symbol:
                    apart.add(i, j)
                elif symbol is _ABS:
                    if apart(x[1], y[1]):
                        apart.add(i, j)
                elif symbol is _APP:
                    if apart(x[1], y[1]) or apart(x[2], y[2]):
                        apart.add(i, j)
                elif symbol is _JOIN:
                    if len(x) != len(y):
                        apart.add(i, j)
                    elif set(x[1:]) != set(y[1:]):
                        # TODO Branch, searching among feasible matchings.
                        # FIXME The following is not complete:
                        apart.add(i, j)
                elif x is not y:
                    apart.add(i, j)

    # Construct the coarsest equivalence relation.
    pending = set(range(len(terms)))
    partitions = []
    while pending:
        seed = pending.pop()
        partition = [seed]
        for i in list(pending):
            if not apart(i, seed):
                pending.remove(i)
                partition.append(i)
        partition.sort()
        partitions.append(partition)
    partitions.sort()

    # Quotient the graph.
    perm = [None] * len(terms)
    for target, part in enumerate(partitions):
        for source in part:
            perm[source] = target
    return graph_permute(terms, perm)


def graph_quotient(terms):
    """Deduplicate equivalent vertices."""
    terms = graph_quotient_weak(terms)
    terms = graph_quotient_strong(terms)
    return terms


def graph_address(terms):
    """Find the least address of each term in a graph, up to nondeterminism.

    This acts as a hashing function for terms in graphs, in that, except for
    nondeterminism, each term has a unique minimum address. Thus graph sorting
    can restrict to permutations within address equivalence class.
    """
    assert all(isinstance(term, Term) for term in terms)
    min_address = [None] * len(terms)
    min_address[0] = ()  # Root address.
    pending = deque([0])
    while pending:
        i = pending.popleft()
        address = min_address[i]
        for direction, j in term_iter_subterms(terms[i]):
            subaddress = address + (direction,)
            if min_address[j] is None or subaddress < min_address[j]:
                min_address[j] = subaddress
                pending.append(j)
    return min_address


def partition_by_address(min_address):
    """Partition terms by address, given min addresses from graph_addres.

    This is partition and the ordering of its parts are both guaranteed to be
    invariant to graph isomorphism, however the ordering of items within parts
    is not invariang under graph isomorphism.
    """
    by_address = defaultdict(list)
    for i, address in enumerate(min_address):
        by_address[address].append(i)
    return [by_address[key] for key in sorted(by_address)]


def partitioned_permutations(partitions):
    factors = map(itertools.permutations, partitions)
    for perms in itertools.product(*factors):
        yield perm_inverse(sum(perms, ()))


def graph_sort(terms):
    """Canonicalize the ordering of vertices in a graph.

    This implementation first sorts terms by an isomorphism-invariant
    address, and then disambiguates address collisions by finding the
    min graph among all graphs with the same address partitions, wrt the
    arbitrary linear order of the python langauge.
    """
    min_address = graph_address(terms)
    partitions = partition_by_address(min_address)
    perms = partitioned_permutations(partitions)
    return min(graph_permute(terms, p) for p in perms)


def graph_make(terms):
    """Make a canonical graph, given a messy list of terms."""
    assert all(isinstance(term, Term) for term in terms)
    terms = graph_prune(terms)
    terms = graph_quotient(terms)
    terms = graph_sort(terms)
    return Graph.make(*terms)


@memoize_args
def extract_subterm(graph, pos):
    """Extract the subterm of a graph at given root position."""
    assert isinstance(pos, int) and 0 <= pos and pos < len(graph), pos
    perm = range(len(graph))
    perm[0] = pos
    perm[pos] = 0
    terms = graph_permute(graph, perm)
    return graph_make(terms)


# ----------------------------------------------------------------------------
# Graph construction (intro forms)

TOP = graph_make([Term.TOP])
BOT = graph_make([Term.JOIN([])])
Y = graph_make([Term.ABS(1), Term.APP(2, 1), Term.VAR(0)])


@memoize_arg
def NVAR(name):
    assert isinstance(name, str), name
    if re_keyword.match(name):
        raise ValueError('Variable names cannot match [A-Z]+: {}'.format(name))
    terms = [Term.NVAR(intern(name))]
    return graph_make(terms)


@memoize_args
def FUN(var, body):
    assert isinstance(var, Graph) and len(var) == 1 and isa_nvar(var), var
    assert isinstance(body, Graph), body
    name = var[0][1]
    body_offset = 1
    terms = [Term.ABS(1)]
    for term in body:
        terms.append(term_shift(term, body_offset))
    for i, term in enumerate(terms):
        if isa_nvar(term) and term[1] == name:
            terms[i] = Term.VAR(0)
    return graph_make(terms)


@memoize_args
def APP(lhs, rhs):
    assert isinstance(lhs, Graph), lhs
    assert isinstance(rhs, Graph), rhs
    lhs_offset = 1
    rhs_offset = 1 + len(lhs)
    terms = [Term.APP(lhs_offset, rhs_offset)]
    for term in lhs:
        terms.append(term_shift(term, lhs_offset))
    for term in rhs:
        terms.append(term_shift(term, rhs_offset))
    return graph_make(terms)


def iter_join(graph):
    """Destruct JOIN terms."""
    if graph[0][0] is _JOIN:
        for pos in graph[0][1:]:
            yield extract_subterm(graph, pos)
    else:
        yield graph


def preprocess_join_args(fun):

    @functools.wraps(fun)
    def join(args):
        args = frozenset(g for arg in args for g in iter_join(arg))
        return fun(args)

    return join


@preprocess_join_args
@memoize_arg
def JOIN(args):
    assert all(isinstance(arg, Graph) for arg in args), args
    # Handle trivial cases.
    if TOP in args:
        return TOP
    if not args:
        return BOT
    if len(args) == 1:
        return next(iter(args))

    # Construct a join term.
    args = list(args)
    offsets = [1]
    for arg in args[:-1]:
        offsets.append(offsets[-1] + len(arg))
    terms = [Term.JOIN(offsets)]
    for arg, offset in itertools.izip(args, offsets):
        for term in arg:
            terms.append(term_shift(term, offset))
    return graph_make(terms)


# ----------------------------------------------------------------------------
# Graph matching (elim forms)

def isa_nvar(graph):
    return graph[0][0] is _NVAR


def isa_var(graph):
    return graph[0][0] is _VAR


def isa_abs(graph):
    return graph[0][0] is _ABS


def isa_app(graph):
    return graph[0][0] is _APP


def isa_join(graph):
    return graph[0][0] is _JOIN
