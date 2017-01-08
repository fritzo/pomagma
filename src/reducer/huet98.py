"""Regular Nondeterministic Bohm Trees.

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

Combinator = namedtuple('Combinator', ['bound', 'head', 'args'])


def make_combinator(bound, head, *args):
    assert isinstance(bound, int) and bound > 0, bound
    assert isinstance(head, int) and 0 <= head and head < bound, head
    for arg in args:
        assert isinstance(arg, tuple) and isinstance(arg[0], str), args
        for var in arg[1:]:
            assert isinstance(var, int) and 0 <= var and var < bound, args
    return Combinator(bound, head, tuple(args))


_I = make_combinator(1, 0)


def eta_expand(comb):
    bound, head, args = comb
    return make_combinator(bound + 1, head, *(args + (('_I', bound),)))


class Presentation(object):
    """Finite presentation of a regular Bohm forest."""

    def __init__(self):
        self._equations = defaultdict(set)
        self._equations['_I'].add(_I)  # Required by eta_expand(-).

    def define(self, name, combinator):
        assert isinstance(name, str), name
        assert name != '_I', name
        assert isinstance(combinator, Combinator), combinator
        self._equations[name].add(combinator)
        for arg in combinator.args:
            self._equations[arg[0]]

    @property
    def deterministic(self):
        return max(map(len, self._equations.values())) <= 1

    def decide_less_deterministic(self, lhs, rhs):
        """Decide Scott ordering between two regular Bohm trees.

        Args: lhs, rhs: names of roots of trees.
        Returns: True or False.
        """
        assert lhs in self._equations, lhs
        assert rhs in self._equations, rhs
        assert self.deterministic

        con = set()
        hyp = set([
            (lc, rc)
            for lc in self._equations[lhs]
            for rc in self._equations[rhs]
        ])
        while hyp:
            focus = hyp.pop()
            if focus in con:
                continue
            con.add(focus)

            lc, rc = focus
            while lc.bound < rc.bound:
                lc = eta_expand(lc)
            while rc.bound < lc.bound:
                rc = eta_expand(rc)
            assert lc.bound == rc.bound
            if lc.head != rc.head or len(lc.args) != len(rc.args):
                return False
            for la, ra in zip(lc.args, rc.args):
                if len(self._equations[la[0]]) == 0:
                    continue
                if len(self._equations[ra[0]]) == 0:
                    return False
                lc = iter(next(self._equations[la[0]]))  # FIXME apply args
                rc = iter(next(self._equations[ra[0]]))  # FIXME apply args
                TODO('apply args to lc, rc')
                if lc == rc or (lc, rc) in con:
                    continue
                hyp.add(la, ra)
        return True

    def decide_less(self, lhs, rhs):
        """Decide Scott ordering between two regular Bohm trees.

        Args: lhs, rhs: names of roots of trees.
        Returns: True or False.
        """
        assert lhs in self._equations, lhs
        assert rhs in self._equations, rhs
        if self.deterministic:
            return self.decide_less_deterministic

        # Each set is a conjunction of disjunctions.
        con = set()
        hyp = set([
            set([(lc, rc) for rc in self._equations[rhs]])
            for lc in self._equations[lhs]
        ])
        while hyp:
            focus = hyp.pop()
            if focus in con:
                continue
            TODO('Implement backtracking')

    def decide_equal(self, lhs, rhs):
        return self.decide_less(lhs, rhs) and self.decide_less(rhs, lhs)
