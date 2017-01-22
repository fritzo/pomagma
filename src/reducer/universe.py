"""A universe of graph terms with full sharing.

Graphs are constructed much like terms in reducer.syntax, but with an extra
level of indirection 'Ob' so as to allow building of cyclic terms.
"""

from pomagma.compiler.util import MEMOIZED_CACHES, memoize_arg, memoize_args
from pomagma.util import TODO

# ----------------------------------------------------------------------------
# Signature

_ob_to_term = []
_term_to_ob = {}


class Ob(int):
    @staticmethod
    def make():
        _ob_to_term.append(None)
        return Ob(len(_ob_to_term) - 1)


class Term(tuple):
    _make_cache = {}

    @staticmethod
    def make(args, ob=None):
        try:
            return Term._make_cache[args]
        except KeyError:
            pass
        term = Term(args)
        if ob is None:
            ob = Ob.make()
        _ob_to_term[ob] = term
        _term_to_ob[term] = ob
        Term._make_cache[args] = term
        return term


MEMOIZED_CACHES[Term.make] = Term._make_cache

_HOLE = intern('HOLE')
_TOP = intern('TOP')
_NVAR = intern('NVAR')
_IVAR = intern('IVAR')
_ABS = intern('ABS')
_APP = intern('APP')
_JOIN = intern('JOIN')

HOLE = Term.make(_HOLE)
TOP = Term.make(_TOP)


def NVAR(name):
    assert isinstance(name, str)
    return Term.make((_NVAR, name))


def IVAR(rank):
    assert isinstance(rank, int) and rank >= 0
    return Term.make((_IVAR, rank))


def ABS(body):
    assert isinstance(body, Ob)
    return Term.make((_ABS, body))


def APP(fun, arg):
    assert isinstance(fun, Ob)
    assert isinstance(arg, Ob)
    return Term.make((_APP, fun, arg))


def JOIN(args):
    assert all(isinstance(arg, Ob) for arg in args)
    return Term.make((_JOIN,) + tuple(sorted(set(args))))


# ----------------------------------------------------------------------------
# Mutual recursion

def term_iter_obs(term):
    assert isinstance(term, Term)
    symbol = term[0]
    if symbol is _ABS:
        yield term[1]
    elif symbol is _APP:
        yield term[1]
        yield term[2]
    elif symbol is _JOIN:
        for ob in term[1:]:
            yield ob


_cyclic_stack = set()


@memoize_arg
def is_cyclic(ob):
    """Return whether ob contains cycles, i.e. is not well founded."""
    assert isinstance(ob, Ob)
    if ob in _cyclic_stack:
        return True
    term = _ob_to_term[ob]
    _cyclic_stack.add(ob)
    result = any(is_cyclic(sub) for sub in term_iter_obs(term))
    _cyclic_stack.remove(ob)
    return result


@memoize_args
def _approximate(term, depth):
    assert is_cyclic(term)
    assert depth > 0
    symbol = term[0]
    if symbol in (_HOLE, _TOP, _IVAR, _NVAR):
        return term
    elif symbol is _ABS:
        body = _term_to_ob[approximate(term[1], depth - 1)]
        return ABS(body)
    elif symbol is _APP:
        lhs = _term_to_ob[approximate(term[1], depth - 1)]
        rhs = _term_to_ob[approximate(term[2], depth - 1)]
        return APP(lhs, rhs)
    elif symbol is _JOIN:
        args = [_term_to_ob[approximate(arg, depth - 1)] for arg in term[1:]]
        return JOIN(args)
    else:
        raise ValueError(term)


def approximate(term, depth):
    """Approximate cyclic portion of term to given depth.

    Approximated subterms will be replaced by HOLE.
    Acyclic subterms will be returned in entirety, possibly exceeding depth.
    """
    assert isinstance(term, Term)
    assert isinstance(depth, int) and depth >= 0
    if not is_cyclic(term):
        return term
    elif depth == 0:
        return HOLE
    else:
        return _approximate(term, depth)


def rec(**defs):
    """Construct a set of mutually recursive graph terms.

    Keyword Args:
      (name = definition) pairs, where any NVAR(name) may occur in any of the
      definitions.

    Returns:
      Dict of (name = definition) pairs, where no NVAR(name) occurs in any of
      the definitions; the definitions now refer to graph terms.
    """
    assert all(isinstance(key, str) for key in defs.keys())
    assert all(isinstance(val, Term) for val in defs.values())
    defs = {NVAR(key): val for key, val in defs.iteritems()}
    TODO('search for existing instances of graph')
    return defs
