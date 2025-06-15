"""
Combinator Graph Reduction.

[1] Philip Koopman (1990)
  "An Architecture for Combinator Graph Reduction"
  https://users.ece.cmu.edu/~koopman/tigre/index.html
"""

import sys

_APP = sys.intern("APP")
_ATOM = sys.intern("ATOM")


def make_equation(lhs, rhs):
    assert lhs is not rhs
    lhs = id(lhs)
    rhs = id(rhs)
    return (lhs, rhs) if lhs <= rhs else (rhs, lhs)


class Node:
    __slots__ = ["typ", "args"]

    def __init__(self, typ, *args):
        self.typ = typ
        self.args = args

    # TODO This does not allow printing of cyclic structures.
    # def __repr__(self):
    #     typ = self[0]
    #     if self.typ is _ATOM:
    #         return "ATOM('{}')".format(self.name)
    #     else:
    #         args = ','.join(str(a) for a in self.args)
    #         return '{}({})'.format(symbol, args)
    #
    # __str__ = __repr__

    @property
    def is_atom(self):
        return self.typ is _ATOM

    @property
    def is_app(self):
        return self.typ is _APP

    @property
    def name(self):
        assert self.is_atom
        return self.args[0]

    @property
    def fun(self):
        assert self.is_app
        return self.args[0]

    # @fun.setter
    def set_fun(self, fun):
        assert self.is_app
        assert isinstance(fun, Node)
        self.args = (fun, self.arg)

    @property
    def arg(self):
        assert self.is_app
        return self.args[1]

    # @arg.setter
    def set_arg(self, arg):
        assert self.is_app
        assert isinstance(arg, Node)
        self.args = (self.fun, arg)

    def copy_from(self, other):
        assert isinstance(other, Node)
        self.typ = other.typ
        self.args = tuple(other.args)

    def copy(self, copies=None):
        """Deep copy."""
        if copies is None:
            copies = {}
        if id(self) in copies:
            return copies[id(self)]
        result = Node(self.typ, *self.args)
        copies[id(self)] = result
        if self.is_app:
            result.set_fun(self.fun.copy(copies))
            result.set_arg(self.arg.copy(copies))
        return result

    def __eq__(self, other):
        """Syntactic equality modulo graph quotient."""
        assert isinstance(other, Node)
        if self is other:
            return True
        node_by_id = {id(self): self, id(other): other}
        hyp = {make_equation(self, other)}
        con = set()
        while hyp:
            eqn = hyp.pop()
            lhs = node_by_id[eqn[0]]
            rhs = node_by_id[eqn[1]]
            if lhs.typ is not rhs.typ:
                return False
            if lhs.is_atom:
                if rhs.name is not lhs.name:
                    return False
                con.add(eqn)
            elif lhs.is_app:
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


def ATOM(name):
    assert isinstance(name, str)
    return Node(_ATOM, sys.intern(name))


def APP(fun, arg):
    assert isinstance(fun, Node)
    assert isinstance(arg, Node)
    return Node(_APP, fun, arg)


TOP = ATOM("TOP")
BOT = ATOM("BOT")
I = ATOM("I")
K = ATOM("K")
B = ATOM("B")
C = ATOM("C")
S = ATOM("S")


def print_to_depth(node, depth=10):
    assert isinstance(node, Node)
    if node.is_atom:
        return node.name
    if node.is_app:
        if depth > 0:
            fun = print_to_depth(node.fun, depth - 1)
            arg = print_to_depth(node.arg, depth - 1)
            return f"APP({fun},{arg})"
        return "APP(...,...)"
    raise ValueError(node)


def try_beta_step(node):
    """Try to perform a beta-step in-place.

    Returns:
        True or False, depending on whether a step was performed.
    """
    assert isinstance(node, Node)
    stack = {id(node)}
    return _try_beta_step(node, stack)


def _try_beta_step(node, stack):
    # print(print_to_depth(node))
    if node.is_atom:
        return False
    if node.is_app:
        if node.fun.is_atom:
            atom = node.fun
            if atom == TOP:
                node.copy_from(TOP)
                return True
            if atom == BOT:
                node.copy_from(BOT)
                return True
            if atom == I:
                node.copy_from(node.arg)
                return True
        elif node.fun.is_app:
            if node.fun.fun.is_atom:
                atom = node.fun.fun
                if atom == K:
                    node.copy_from(node.fun.arg)
                    return True
            elif node.fun.fun.is_app:
                if node.fun.fun.fun.is_atom:
                    atom = node.fun.fun.fun
                    x = node.fun.fun.arg
                    y = node.fun.arg
                    z = node.arg
                    if atom == B:
                        node.copy_from(APP(x, APP(y, z)))
                        return True
                    if atom == C:
                        node.copy_from(APP(APP(x, z), y))
                        return True
                    if atom == S:
                        node.copy_from(APP(APP(x, z), APP(y, z)))
                        return True
        for subnode in node.args:
            if id(subnode) in stack:
                return False
            stack.add(id(subnode))
            step = _try_beta_step(subnode, stack)
            stack.remove(id(subnode))
            if step:
                return True
        return False
    raise ValueError(node)


def count_beta_steps(node):
    """Returns number of reduction steps."""
    assert isinstance(node, Node)
    count = 0
    while try_beta_step(node):
        count += 1
    return count
