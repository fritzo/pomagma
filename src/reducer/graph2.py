"""Lambda term graph reduction.

This is similar to reducer.graph, but relies on python object references rather
than explicit int pointers. This can also be seen as a lambda-caclulus version
of reducer.koopman's combinatory graph reduction.

This implementation aims for correctness rather than efficiency. Hence graphs
are .copy()ed more often than needed, and there is minimal sharing.
"""

from pomagma.compiler.util import memoize_arg
from pomagma.reducer.util import logged
import sys

DEFAULT_DEPTH = 10

# ----------------------------------------------------------------------------
# Signature

_ATOM = sys.intern("ATOM")
_VAR = sys.intern("VAR")
_ABS = sys.intern("ABS")
_APP = sys.intern("APP")


def make_equation(lhs, rhs):
    assert lhs is not rhs
    lhs = id(lhs)
    rhs = id(rhs)
    return (lhs, rhs) if lhs <= rhs else (rhs, lhs)


class Node(object):
    """Mutable node in a term graph."""

    __slots__ = ["typ", "args"]

    def __init__(self, typ, *args):
        self.typ = typ
        self.args = args

    def copy_from(self, other):
        assert isinstance(other, Node)
        assert is_app(self)
        self.typ = other.typ
        self.args = other.args

    def copy(self, results=None):
        """Deep copy ABS and APP terms; do not copy ATOMs or VARs."""
        if self.typ is _ATOM or self.typ is _VAR:
            return self
        if results is None:
            results = {}
        elif id(self) in results:
            return results[id(self)]
        result = Node(self.typ, *self.args)
        results[id(self)] = result
        result.args = tuple(arg.copy(results) for arg in self.args)
        return result

    def __eq__(self, other):
        """Syntactic equality modulo graph quotient (i.e. bisimilarity)."""
        assert isinstance(other, Node)
        if self is other:
            return True
        node_by_id = {id(self): self, id(other): other}
        hyp = set([make_equation(self, other)])
        con = set()
        while hyp:
            eqn = hyp.pop()
            lhs = node_by_id[eqn[0]]
            rhs = node_by_id[eqn[1]]
            if lhs.typ is not rhs.typ:
                return False
            elif is_atom(lhs):
                if rhs.args[0] is not lhs.args[0]:
                    return False
                con.add(eqn)
            else:
                con.add(eqn)
                for lhs, rhs in zip(lhs.args, rhs.args):
                    if lhs is rhs:
                        continue
                    node_by_id[id(lhs)] = lhs
                    node_by_id[id(rhs)] = rhs
                    eqn = make_equation(lhs, rhs)
                    if eqn not in con:
                        hyp.add(eqn)
        return True

    def print_to_depth(self, depth=10):
        if self.typ == _ATOM:
            return self.args[0]
        else:
            if depth > 0:
                args = [arg.print_to_depth(depth - 1) for arg in self.args]
            else:
                args = ["..."] * len(self.args)
            return "{}({})".format(self.typ, ",".join(args))

    def __str__(self):
        return self.print_to_depth(DEFAULT_DEPTH)


@memoize_arg
def ATOM(name):
    assert isinstance(name, str)
    return Node(_ATOM, sys.intern(name))


HOLE = ATOM("HOLE")

_VAR_CACHE = {}


# Memoized by id(node).
def VAR(node):
    assert isinstance(node, Node) and is_abs(node)
    return _VAR_CACHE.setdefault(id(node), Node(_VAR, node))


def ABS(body):
    assert isinstance(body, Node)
    return Node(_ABS, body)


def APP(fun, arg):
    assert isinstance(fun, Node)
    assert isinstance(arg, Node)
    return Node(_APP, fun, arg)


def is_atom(node):
    assert isinstance(node, Node)
    return node.typ is _ATOM


def is_var(node):
    assert isinstance(node, Node)
    return node.typ is _VAR


def is_abs(node):
    assert isinstance(node, Node)
    return node.typ is _ABS


def is_app(node):
    assert isinstance(node, Node)
    return node.typ is _APP


# ----------------------------------------------------------------------------
# Substitution


@logged(str, str, str, str, returns=str)
def _substitute(old, new, node, results):
    key = id(node)
    if key not in results:
        if is_atom(node) or is_var(node):
            # While '==' is quite expensive, 'is' would not suffice.
            results[key] = new if node == old else node
        elif is_abs(node) or is_app(node):
            result = node.copy()
            results[key] = result  # This must be set before recursing.
            result.args = tuple(
                _substitute(old, new, arg, results) for arg in node.args
            )
        else:
            raise ValueError(node)
    return results[key]


@logged(str, str, str, returns=str)
def substitute(old, new, node):
    """Substitute old for new in node."""
    assert isinstance(old, Node)
    assert is_atom(old) or is_var(old), "old must be is-comparable"
    assert isinstance(new, Node)
    assert isinstance(node, Node)
    return _substitute(old, new, node, {})


def NVAR(name):
    return ATOM(name)


def FUN(nvar, body):
    assert isinstance(nvar, Node) and is_atom(nvar)
    assert isinstance(body, Node)
    result = ABS(HOLE)
    body = substitute(nvar, VAR(result), body)
    result.args = (body,)
    return result


# ----------------------------------------------------------------------------
# Reduction


@logged(str, returns=str)
def try_beta_step(node):
    """Tries to reduce a node in-place. Returns False if node is normal."""
    assert isinstance(node, Node)
    if is_atom(node) or is_var(node):
        return False
    elif is_abs(node):
        body = node.args[0]
        return try_beta_step(body)
    elif is_app(node):
        fun, arg = node.args
        if is_abs(fun):
            var = VAR(fun)
            body = fun.args[0]
            node.copy_from(substitute(var, arg, body))
            return True
        else:
            return try_beta_step(fun) or try_beta_step(arg)
    else:
        raise ValueError(node)
