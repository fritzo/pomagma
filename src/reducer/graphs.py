"""Rational Term Graphs.

Graphs are represented as tuples of function symbols applied to vertex ids,
where the 0th location of the tuple is the root.

This rooted graph data structure intends to represent terms just coarsely
enough to enable cons hashing modulo isomorphism of rooted graphs. In
particular, we choose fintary JOIN over binary JOIN so as to ease the
isomorphism problem: JOIN terms are syntactically accociative, commutative, and
idempotent.

The implementation of abstraction as ABS,VAR is a little unusual in that an ABS
term points only to its body and each VAR points back to its abstraction. After
graph_quotient_weak(-), there should be at most one VAR pointing to each
abstraction. This implementation of abstraction makes it easy to collect
garbage in graph_prune(-), and makes substitution easier than it would be with
de Bruijn indices (which are complex in the presence of cycles [1]).

Sharing is accomplished at two levels: term nodes are shared among graphs and
graphs are shared among computations (by memoization). While this form of
sharing is weaker than that of cons hashed terms, it is well suited to modern
architectures, since graphs are compact arrays of pointers to terms. This
format translates well to C/C++, where terms can be atoms, graphs can be arrays
of small 16 bit or 32 bit pointers to terms, and hashing is cheap.

[1] "Lazy Specialization" (1999) Michael Jonathan Thyer
  http://thyer.name/phd-thesis/thesis-thyer.pdf

"""

import functools
import inspect
import itertools
import re
from collections import defaultdict, deque

from pomagma.compiler.util import memoize_arg, memoize_args
from pomagma.reducer import syntax
from pomagma.reducer.util import UnreachableError
from pomagma.util import TODO

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
        elif symbol is _JOIN:
            args = ','.join(str(a) for a in self[1:])
            return '{}([{}])'.format(symbol, args)
        else:
            args = ','.join(str(a) for a in self[1:])
            return '{}({})'.format(symbol, args)

    __str__ = __repr__

    @staticmethod
    @memoize_args
    def make(*args):
        return Term(args)

    TOP = None  # Defined below.

    @staticmethod
    def NVAR(name):
        assert isinstance(name, str), name
        name = intern(name)
        return Term.make(_NVAR, name)

    @staticmethod
    def VAR(abs_):
        assert isinstance(abs_, int) and abs_ >= 0, abs
        return Term.make(_VAR, abs_)

    @staticmethod
    def ABS(body):
        assert isinstance(body, int) and body >= 0, body
        return Term.make(_ABS, body)

    @staticmethod
    def APP(lhs, rhs):
        assert isinstance(lhs, int) and lhs >= 0, lhs
        assert isinstance(rhs, int) and rhs >= 0, rhs
        return Term.make(_APP, lhs, rhs)

    @staticmethod
    def JOIN(args):
        args = sorted(set(args))
        for arg in args:
            assert isinstance(arg, int) and arg >= 0, arg
        return Term.make(_JOIN, *args)

    @property
    def is_nvar(self):
        return self[0] is _NVAR

    @property
    def is_var(self):
        return self[0] is _VAR

    @property
    def is_abs(self):
        return self[0] is _ABS

    @property
    def is_app(self):
        return self[0] is _APP

    @property
    def is_join(self):
        return self[0] is _JOIN


Term.TOP = Term.make(_TOP)


class Graph(tuple):
    @staticmethod
    @memoize_args
    def make(*args):
        return Graph(args)

    def pretty(self):
        return '\n'.join(
            '{} = {}'.format(pos, term)
            for pos, term in enumerate(self)
        )

    @property
    def is_nvar(self):
        return self[0].is_nvar

    @property
    def is_var(self):
        return self[0].is_var

    @property
    def is_abs(self):
        return self[0].is_abs

    @property
    def is_app(self):
        return self[0].is_app

    @property
    def is_join(self):
        return self[0].is_join

    __call__ = None  # Defined below.
    __or__ = None  # Defined below.


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


def graph_reachable_by(graph, pos):
    """Return set of positions reachable by pos."""
    assert isinstance(graph, Graph)
    assert isinstance(pos, int) and 0 <= pos and pos < len(graph), pos
    result = set([])
    pending = set([pos])
    while pending:
        pos = pending.pop()
        result.add(pos)
        term = graph[pos]
        for _, pos in term_iter_subterms(term):
            if pos not in result:
                pending.add(pos)
    return result


def subterm_is_closed(graph, pos):
    """Whether for each reachable VAR, its ABS binder is reachable."""
    reachable = graph_reachable_by(graph, pos)
    for var_pos in reachable:
        var_term = graph[var_pos]
        if var_term.is_var:
            abs_pos = var_term[1]
            if abs_pos not in reachable:
                return False
    return True


@memoize_args
def extract_subterm(graph, pos):
    """Extract the subterm of a graph at given root position."""
    assert isinstance(graph, Graph)
    assert isinstance(pos, int) and 0 <= pos and pos < len(graph), pos
    assert subterm_is_closed(graph, pos)  # TODO Relax this.
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
    """Create a named variable Graph."""
    assert isinstance(name, str), name
    if re_keyword.match(name):
        raise ValueError('Variable names cannot match [A-Z]+: {}'.format(name))
    terms = [Term.NVAR(intern(name))]
    return graph_make(terms)


@memoize_args
def FUN(var, body):
    """Abstract an NVAR Graph from another Graph."""
    assert isinstance(var, Graph) and len(var) == 1 and var.is_nvar, var
    assert isinstance(body, Graph), body
    name = var[0][1]
    body_offset = 1
    terms = [Term.ABS(1)]
    for term in body:
        terms.append(term_shift(term, body_offset))
    for i, term in enumerate(terms):
        if term.is_nvar and term[1] is name:
            terms[i] = Term.VAR(0)
    return graph_make(terms)


@memoize_args
def APP(lhs, rhs):
    """Apply one graph to another."""
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
    """Destruct JOIN terms, yielding graphs."""
    term = graph[0]
    if term.is_join:
        for pos in term[1:]:
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
    """Join a collection of graphs."""
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
# Syntax

def as_graph(fun):
    """Convert lambdas to graphs using Higher Order Abstract Syntax [1].

    [1] Pfenning, Elliot (1988) "Higher-order abstract syntax"
      https://www.cs.cmu.edu/~fp/papers/pldi88.pdf
    """
    if isinstance(fun, Graph):
        return fun
    if not callable(fun):
        raise SyntaxError('Expected callable, got: {}'.format(fun))
    args, vargs, kwargs, defaults = inspect.getargspec(fun)
    if vargs or kwargs or defaults:
        source = inspect.getsource(fun)
        raise SyntaxError('Unsupported signature: {}'.format(source))
    symbolic_args = map(NVAR, args)
    symbolic_result = fun(*symbolic_args)
    graph = as_graph(symbolic_result)
    for var in reversed(symbolic_args):
        graph = FUN(var, graph)
    return graph


def graph_apply(fun, *args):
    """Currying wrapper around APP(-,-)."""
    result = fun
    for arg in args:
        arg = as_graph(arg)
        result = APP(result, arg)
    return result


def graph_join(lhs, rhs):
    rhs = as_graph(rhs)
    return JOIN([lhs, rhs])


Graph.__call__ = graph_apply
Graph.__or__ = graph_join

I = as_graph(lambda x: x)
K = as_graph(lambda x, y: x)
B = as_graph(lambda x, y, z: x(y(z)))
C = as_graph(lambda x, y, z: x(z, y))
S = as_graph(lambda x, y, z: x(z, y(z)))

KI = as_graph(lambda x, y: y)
CB = as_graph(lambda x, y, z: y(x(z)))
CI = as_graph(lambda x, y: y(x))

SIGNATURE = {
    'TOP': TOP,
    'BOT': BOT,
    'NVAR': NVAR,
    'APP': graph_apply,
    'JOIN': graph_join,
    'FUN': FUN,
    'I': I,
    'K': K,
    'B': B,
    'C': C,
    'S': S,
}

convert = syntax.Transform(**SIGNATURE)


# ----------------------------------------------------------------------------
# Scott ordering

def dominates(lhs, rhs):
    """Weak strict domination relation: lhs =] rhs and lhs [!= rhs."""
    lhs_rhs = try_decide_less(lhs, rhs)
    rhs_lhs = try_decide_less(rhs, lhs)
    return rhs_lhs is True and lhs_rhs is False


@memoize_args
def try_decide_less(lhs, rhs):
    """Weak decision procedure returning True, False, or None."""
    assert isinstance(lhs, Graph), lhs
    assert isinstance(rhs, Graph), rhs

    # Try simple cases.
    if lhs is BOT or lhs is rhs or rhs is TOP:
        return True
    if lhs is TOP and rhs is BOT:
        return False

    # TODO Try harder.

    # Give up.
    return None


# ----------------------------------------------------------------------------
# Variables

@memoize_arg
def _free_vars(graph):
    result = [set() for _ in xrange(len(graph))]
    for pos, term in enumerate(graph):
        if term.is_var:
            result[pos].add(term)
    changed = True
    while changed:
        changed = False
        for pos, term in enumerate(graph):
            if term is Term.TOP or term.is_nvar or term.is_var:
                continue
            elif term.is_abs:
                arg_pos = term[1]
                for var in result[arg_pos]:
                    if var[1] != pos:  # Bind.
                        if var not in result[pos]:
                            changed = True
                            result[pos].add(var)
            elif term.is_app or term.is_join:
                for arg_pos in term[1:]:
                    for var in result[arg_pos]:
                        if var not in result[pos]:
                            changed = True
                            result[pos].add(var)
            else:
                raise UnreachableError(term)
    return tuple(frozenset(r) for r in result)  # Freeze.


def free_vars(graph, pos):
    """Return frozenset of Terms representing free vars of graph[pos]."""
    return _free_vars(graph)[pos]


def _var_is_linear(graph, var_pos):
    """Whether no terms of a graph ever copy the given bound variable."""
    assert isinstance(graph, Graph)
    assert isinstance(var_pos, int)
    assert 0 <= var_pos and var_pos < len(graph)
    assert graph[var_pos].is_var
    counts = [0] * len(graph)
    counts[var_pos] = 1

    # Propagate in reverse order.
    # Most graphs should converge after two iterations.
    schedule = [
        (i, term)
        for i, term in enumerate(graph)
        if term[0] not in (_TOP, _NVAR, _VAR)
    ]
    schedule.reverse()

    # Propagate until convergence.
    changed = True
    while changed:
        changed = False
        for i, term in schedule:
            symbol = term[0]
            if symbol is _ABS:
                count = counts[term[1]]
            elif symbol is _APP:
                count = counts[term[1]] + counts[term[2]]
            elif symbol is _JOIN:
                if len(term) == 1:
                    count = 0
                else:
                    count = max(counts[j] for j in term[1:])
            else:
                raise UnreachableError(symbol)
            if count > 1:
                return False
            if count != counts[i]:
                counts[i] = count
                changed = True
    return True


@memoize_arg
def is_linear(graph):
    """Whether no terms of a graph ever copy any bound variable.

    Note that JOIN is not considered copying.
    """
    assert isinstance(graph, Graph)
    return all(
        _var_is_linear(graph, pos)
        for pos, var in enumerate(graph)
        if var.is_var
    )


# ----------------------------------------------------------------------------
# Reduction

class Substitution(dict):
    def __call__(self, key):
        return self.get(key, key)

    def map_term(self, term):
        assert isinstance(term, Term)
        if term is Term.TOP:
            return term
        elif term.is_nvar:
            return term
        elif term.is_var:
            return Term.VAR(self(term[1]))
        elif term.is_abs:
            return Term.ABS(self(term[1]))
        elif term.is_app:
            return Term.APP(self(term[1]), self(term[2]))
        elif term.is_join:
            return Term.JOIN([self(pos) for pos in term[1:]])
        else:
            raise ValueError(term)

    def map_terms(self, terms):
        assert all(isinstance(term, Term) for term in terms)
        return [self.map_term(term) for term in terms]


def _copy_abs_body(terms, app_pos):
    """Copies the ABS body in a beta redex."""
    app_term = terms[app_pos]
    assert app_term.is_app
    abs_pos = app_term[1]
    abs_term = terms[abs_pos]
    assert abs_term.is_abs
    body_pos = abs_term[1]

    # Collect positions to copy.
    pending = set([body_pos])
    to_copy = set()
    while pending:
        pos = pending.pop()
        to_copy.add(pos)
        term = terms[pos]
        for _, sub_pos in term_iter_subterms(term):
            if sub_pos in to_copy or sub_pos in pending:
                continue
            # Avoid copying the APP, to allow infinite parallel beta steps.
            if sub_pos == app_pos:
                continue
            pending.add(sub_pos)

    # Copy terms.
    to_copy = sorted(to_copy)
    shift = len(to_copy)
    old2new = Substitution({
        old_pos: shift + i
        for i, old_pos in enumerate(to_copy)
    })
    for old_pos in to_copy:
        old_term = terms[old_pos]
        new_term = old2new.map_term(old_term)
        terms.append(new_term)

    # Find new body_pos and optional var_pos.
    abs_pos = old2new(abs_pos)
    body_pos = old2new(body_pos)
    var = Term.VAR(abs_pos)
    try:
        var_pos = terms.index(var)
    except ValueError:
        var_pos = None
    return body_pos, var_pos


def _app_abs_step(graph, app_pos):
    """Simple naive beta reduction step."""
    assert isinstance(graph, Graph)
    assert isinstance(app_pos, int) and 0 <= app_pos and app_pos < len(graph)
    app_term = graph[app_pos]
    assert app_term.is_app
    abs_pos = app_term[1]
    arg_pos = app_term[2]
    abs_term = graph[abs_pos]
    assert abs_term.is_abs
    body_pos = abs_term[1]
    terms = list(graph)

    if app_pos == 0:
        TODO('re-root graph')
    body_pos, var_pos = _copy_abs_body(terms, app_pos)
    subs = Substitution({app_pos: body_pos})
    if var_pos is not None:
        subs[var_pos] = arg_pos
    terms = subs.map_terms(terms)
    return graph_make(terms)


def _top_step(graph, pos, top_pos):
    """Replace each occurrence of pos by top_pos."""
    assert isinstance(graph, Graph)
    assert isinstance(pos, int) and 0 <= pos and pos < len(graph)
    assert isinstance(top_pos, int) and 0 <= top_pos and top_pos < len(graph)
    assert graph[top_pos] is Term.TOP

    if pos == 0:
        return TOP
    subs = Substitution({pos, top_pos})
    terms = subs.map_terms(graph)
    return graph_make(terms)


def _app_join_step(graph, app_pos):
    assert isinstance(graph, Graph)
    assert isinstance(app_pos, int) and 0 <= app_pos and app_pos < len(graph)
    app_term = graph[app_pos]
    assert app_term.is_app
    fun_term = graph[app_term[1]]
    assert fun_term.is_join

    if app_pos == 0:
        TODO('re-root graph')
    TODO('Distribute APP over JOIN')


def _abs_join_step(graph, abs_pos):
    assert isinstance(graph, Graph)
    assert isinstance(abs_pos, int) and 0 <= abs_pos and abs_pos < len(graph)
    abs_term = graph[abs_pos]
    assert abs_term.is_abs
    fun_term = graph[abs_term[1]]
    assert fun_term.is_join

    if abs_pos == 0:
        TODO('re-root graph')
    TODO('Distribute ABS over JOIN')


def _eta_step(graph, pos, fun_pos):
    assert isinstance(graph, Graph)
    assert isinstance(pos, int) and 0 <= pos and pos < len(graph)
    assert isinstance(fun_pos, int) and 0 <= fun_pos and fun_pos < len(graph)

    if pos == 0:
        TODO('re-root graph')
    subs = Substitution({pos: fun_pos})
    terms = subs.map_terms(graph)
    return graph_make(terms)


@memoize_arg
def try_compute_step(graph):
    """Tries to execute one compute step.

    Returns: reduced graph if possible, otherwise None.
    """
    assert isinstance(graph, Graph)
    for pos, term in enumerate(graph):
        if term.is_app:
            fun_pos = term[1]
            fun_term = graph[fun_pos]
            if fun_term is Term.TOP:
                return _top_step(graph, pos)
            elif fun_term.is_abs:
                return _app_abs_step(graph, pos)
            elif fun_term.is_join:
                return _app_join_step(graph, pos)
        elif term.is_abs:
            body_pos = term[1]
            body_term = graph[body_pos]
            if body_term is Term.TOP:
                return _top_step(graph, pos, body_pos)
            elif body_term.is_join:
                return _abs_join_step(graph, pos)
            elif body_term.is_app:
                _, fun_pos, var_pos = body_term
                var_term = graph[var_pos]
                if var_term.is_var:
                    if var_term not in free_vars(graph, fun_pos):
                        return _eta_step(graph, pos, fun_pos)
        elif term.is_join:
            for top_pos in term[1:]:
                if graph[top_pos] is Term.TOP:
                    return _top_step(graph, pos, top_pos)
    return None
