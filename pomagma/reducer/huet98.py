r"""Regular Nondeterministic Bohm Trees.

This module implements data structures and decision procedures for regular
Bohm trees as described by Gerard Huet (1998). It generalizes Huet's
presentations by allowing bounded nondeterminism and generalizes Huet's
extensional equality to Scott ordering.

@article{huet1998regular,
  title={Regular b{\"o}hm trees},
  author={Huet, G{\'e}rard},
  journal={Mathematical Structures in Computer Science},
  volume={8},
  number={06},
  pages={671--680},
  year={1998},
  publisher={Cambridge Univ Press},
  url={http://pauillac.inria.fr/~huet/PUBLIC/RBT2.pdf},
}

"""

from collections import defaultdict, namedtuple

from pomagma.util import TODO

Pattern = namedtuple("Pattern", ["head", "args"])
Headex = namedtuple("Headex", ["head", "args"])
Combinator = namedtuple("Combinator", ["bound", "headex"])


def is_nvar(thing):
    return isinstance(thing, str)


def is_ivar(thing):
    return isinstance(thing, int) and thing >= 0


def make_pattern(head, *args):
    assert is_nvar(head)
    assert all(is_ivar(arg) for arg in args)
    return Pattern(head, args)


def make_headex(head, *args):
    assert is_ivar(head)
    assert all(isinstance(arg, Pattern) for arg in args)
    return Headex(head, args)


def make_combinator(bound, headex):
    assert isinstance(bound, int) and bound >= 0
    assert isinstance(headex, Headex)
    return Combinator(bound, headex)


def free_vars(headex):
    assert isinstance(headex, Headex)
    result = {headex.head}
    for patt in headex.args:
        for var in patt.args:
            result.add(var)
    return result


def is_closed(comb):
    assert isinstance(comb, Combinator)
    return max(free_vars(comb.headex)) < comb.bound


_I = make_combinator(1, make_headex(0))
assert is_closed(_I)


def eta_expand(comb):
    assert isinstance(comb, Combinator)
    bound, (head, args) = comb
    args += (make_pattern("_I", bound),)
    bound += 1
    return make_combinator(bound, make_headex(head, *args))


def substitute_headex(headex, src, dst):
    assert isinstance(headex, Headex)
    assert is_ivar(src)
    assert is_ivar(dst)
    head = dst if headex.head == src else headex.head
    args = [substitute_pattern(patt, src, dst) for patt in headex.args]
    return make_headex(head, *args)


def substitute_pattern(patt, src, dst):
    assert isinstance(patt, Pattern)
    assert is_ivar(src)
    assert is_ivar(dst)
    args = [dst if arg == src else arg for arg in patt.args]
    return make_pattern(patt.head, *args)


def app(comb, *args):
    assert isinstance(comb, Combinator)
    assert all(is_ivar(arg) for arg in args)
    assert all(arg >= comb.bound for arg in args), "variable name conflict"
    bound, headex = comb
    for arg in args:
        if bound:
            bound -= 1
            headex = substitute_headex(headex, bound, arg)
        else:
            headex = make_headex(
                headex.head,
                (*headex.args, make_pattern("_I", arg)),
            )
    return make_combinator(bound, headex)


class Presentation:
    """Finite presentation of a regular Bohm forest."""

    def __init__(self):
        self._equations = defaultdict(set)
        self._equations["_I"].add(_I)  # Required by eta_expand(-).

    def define(self, name, combinator):
        assert is_nvar(name) and name != "_I"
        assert isinstance(combinator, Combinator) and is_closed(combinator)
        self._equations[name].add(combinator)
        for patt in combinator.headex.args:
            self._equations[patt.head]

    @property
    def is_deterministic(self):
        return all(len(body) <= 1 for body in list(self._equations.values()))

    def match_combinator(self, lhs, rhs, hyp):
        assert isinstance(lhs, Combinator), lhs
        assert isinstance(rhs, Combinator), rhs
        while lhs.bound < rhs.bound:
            lhs = eta_expand(lhs)
        while rhs.bound < lhs.bound:
            rhs = eta_expand(rhs)
        assert lhs.bound == rhs.bound
        return self.match_headex(lhs.headex, rhs.headex)

    def match_headex(self, lhs, rhs, hyp):
        assert isinstance(lhs, Headex)
        assert isinstance(rhs, Headex)
        if lhs.head != rhs.head or len(lhs.args) != len(rhs.args):
            return False
        for l, r in zip(lhs.args, rhs.args):
            self.match_pattern(l, r, hyp)
        return True

    def match_pattern(self, lhs, rhs, hyp):
        assert isinstance(lhs, Pattern), lhs
        assert isinstance(rhs, Pattern), rhs
        lhs_comb = self._equations[lhs.head]
        rhs_comb = self._equations[rhs.head]
        max_bound = max(lhs_comb.bound, rhs_comb.bound)
        rename = {
            old: new + max_bound
            for new, old in enumerate(sorted(set(lhs.args + rhs.args)))
        }
        lhs = app(self._equations[lhs.head], *[rename[v] for v in lhs.args])
        rhs = app(self._equations[rhs.head], *[rename[v] for v in rhs.args])
        if lhs != rhs:
            hyp.add((lhs, rhs))

    def decide_less_deterministic(self, lhs, rhs):
        """Decide Scott ordering between two deterministic regular Bohm trees.

        Args: lhs, rhs: names of roots of trees.
        Returns: True or False.

        """
        assert lhs in self._equations
        assert rhs in self._equations
        assert self.is_deterministic

        con = set()
        hyp = {(lc, rc) for lc in self._equations[lhs] for rc in self._equations[rhs]}
        while hyp:
            focus = hyp.pop()
            if focus in con:
                continue
            con.add(focus)
            if not self.match_combinator(*focus):
                return False
        return True

    def decide_less(self, lhs, rhs):
        """Decide Scott ordering between two regular Bohm trees.

        Args: lhs, rhs: names of roots of trees.
        Returns: True or False.

        """
        assert lhs in self._equations
        assert rhs in self._equations
        if self.is_deterministic:
            return self.decide_less_deterministic

        # Each set is a conjunction of disjunctions.
        con = set()
        hyp = {{(lc, rc) for rc in self._equations[rhs]} for lc in self._equations[lhs]}
        while hyp:
            focus = hyp.pop()
            if focus in con:
                continue
            TODO("Implement backtracking")
        return None

    def decide_equal(self, lhs, rhs):
        return self.decide_less(lhs, rhs) and self.decide_less(rhs, lhs)
