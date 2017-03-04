r"""Systems of combinators in nearly head normal form.

This aims to generalize Huet's Regular Bohm Trees [1] to non-normal terms.
Whereas Huet restricted combinators to \x1,...,xm. xm M1 ... Mn (where
x1,...,xm are local variables (here IVARs) and each argument M is a single
combinatator variable (here NVARs) followed by local variables), we restrict to
arbitrary normal closed terms of the form \x1,....,xm. M (where M is an
ABS-free term (i.e. M can contain local variables (IVARs), combinator variables
(NVARs), APP(-,-), JOIN(-,-), and atoms like TOP, BOT).

Reduction is accomplished by unfolding the first definition whose head is a
combinator var, then reducing (which is not guaranteed to terminate).

[1] Gerard Huet (1998) "Regular Bohm Trees"
    http://pauillac.inria.fr/~huet/PUBLIC/RBT2.pdf
"""

import sys
from collections import OrderedDict

from pomagma.compiler.util import memoize_arg
from pomagma.reducer import bohm
from pomagma.reducer.syntax import (BOT, NVAR, TOP, Term, free_vars, is_closed,
                                    isa_abs, isa_app, isa_atom, isa_ivar,
                                    isa_join, isa_nvar, sexpr_print)
from pomagma.util import TODO


def log_error(message):
    sys.stderr.write(message)
    sys.stderr.write('\n')
    sys.stderr.flush()


@memoize_arg
def is_abs_free(term):
    """Whether term has no ABS subterms."""
    assert isinstance(term, Term)
    if isa_abs(term):
        return False
    elif isa_atom(term) or isa_ivar(term) or isa_nvar(term):
        return True
    elif isa_app(term):
        return is_abs_free(term[1]) and is_abs_free(term[2])
    elif isa_join(term):
        return all(is_abs_free(part) for part in bohm.iter_join(term))
    else:
        raise ValueError(term)


@memoize_arg
def is_valid_body(term):
    """Whether a term is a valid body of a definition.

    Valid terms:
    * must be closed (no free IVARs)
    * must be normal
    * must have ABS only at the top level
    * cannot be TOP or BOT.
    """
    assert isinstance(term, Term)
    if not is_closed(term):
        log_error('Not closed: {}'.format(term))
        return False
    if not bohm.is_normal(term):
        log_error('Not normal: {}'.format(term))
        return False
    if term is TOP or term is BOT:
        log_error('Disallowed: {}'.format(term))
        return False
    if isa_join(term):
        return all(is_valid_body(part) for part in bohm.iter_join(term))
    while isa_abs(term):
        term = term[1]
    if not is_abs_free(term):
        log_error('ABS in inner term: {}'.format(term))
        return False
    return True


class System(object):
    """System of mutually recursive combinators."""

    def __init__(self, **defs):
        self._defs = OrderedDict()  # : NVAR -> closed Term
        for name, body in sorted(defs.iteritems()):
            NVAR(name)  # Asserts that name is not a keyword.
            self._set(name, body)
        assert self.is_closed()

    def _set(self, name, body):
        assert isinstance(name, str), name
        assert isinstance(body, Term), body
        assert is_valid_body(body), body
        self._defs[name] = body

    def define(self, **kwargs):
        for name, body in kwargs.iteritems():
            assert name not in self._defs, 'Use .update(-,-) instead'
            self._set(name, body)
        assert self.is_closed()

    def update(self, name, body):
        assert name in self._defs, 'Use .define(name=body) instead'
        self._set(name, body)
        assert self.is_closed()

    def copy(self):
        result = System()
        result._defs = self._defs.copy()
        return result

    def __getitem__(self, name):
        assert isinstance(name, str)
        return self._defs[name]

    def __iter__(self):
        return self._defs.iteritems()

    def __eq__(self, other):
        return self._defs == other._defs

    def __repr__(self):
        defs = [
            '{}={}'.format(name, body)
            for name, body in self._defs.iteritems()
        ]
        return 'System({})'.format(', '.join(defs))

    __str__ = __repr__

    def pretty(self):
        width = max(len(name) for name, body in self)
        return '\n'.join(
            '{} = {}'.format(name.rjust(width), sexpr_print(body))
            for name, body in self
        )

    def is_closed(self):
        """Whether all free NVARs are defined."""
        return all(
            var[1] in self._defs
            for body in self._defs.itervalues()
            for var in free_vars(body)
        )


@memoize_arg
def is_unfoldable(body):
    assert isinstance(body, Term)
    # TODO Allow open terms to be unfolded.
    # assert is_valid_body(body)
    if isa_join(body):
        return any(is_unfoldable(term) for term in bohm.iter_join(body))
    while isa_abs(body):
        body = body[1]
    while isa_app(body):
        body = body[1]
    return isa_nvar(body)


def unfold(system, body):
    """Unfold the head variables in body via definitions in system.

    Note that due to JOIN terms, there may be multiple head variables.
    """
    assert isinstance(system, System)
    assert isinstance(body, Term)
    if isa_atom(body) or isa_ivar(body):
        return body
    if isa_nvar(body):
        return system[body[1]]

    # Get a linear normal form.
    if isa_app(body):
        body = bohm.app(unfold(system, body[1]), body[2])  # Only unfold head.
    elif isa_abs(body):
        body = bohm.abstract(unfold(system, body[1]))
    elif isa_join(body):
        body = bohm.join(unfold(system, part) for part in bohm.iter_join(body))
    else:
        raise ValueError(body)

    # Reduce.
    return bohm.reduce(body, budget=1234567890)


def try_beta_step(system):
    assert isinstance(system, System)
    assert system.is_closed()
    for name, body in system:
        if is_unfoldable(body):
            unfolded = unfold(system, body)
            system.update(name, unfolded)
            return True
    return False


# ----------------------------------------------------------------------------
# Decision procedures

class Theory(object):
    def __init__(self):
        self._hyp = set()
        self._con = set()

    def assume_equal(self, lhs, rhs):
        if lhs is rhs:
            return
        eqn = (lhs, rhs) if lhs < rhs else (rhs, lhs)
        if eqn not in self._con:
            self._hyp.add(eqn)

    def conclude_equal(self, lhs, rhs):
        if lhs is rhs:
            return
        eqn = (lhs, rhs) if lhs < rhs else (rhs, lhs)
        self._con.add(eqn)

    def has_assumptions(self):
        return bool(self._hyp)

    def pop(self):
        # TODO Prioritize to ensure progress.
        return self._hyp.pop()


# Adapted from bohm.try_decide_less_weak(-,-).
def try_match_equal(system, theory, lhs, rhs):
    assert isinstance(system, System)
    assert isinstance(theory, Theory)
    assert isinstance(lhs, Term)
    assert isinstance(rhs, Term)

    # Distinguish atoms and local variables.
    if isa_ivar(lhs) or lhs is TOP or lhs is BOT:
        if isa_ivar(rhs) or rhs is TOP or rhs is BOT:
            return lhs is rhs

    # Destructure JOIN.
    if isa_join(lhs) or isa_join(rhs):
        TODO('handle JOIN')

    # Destructure ABS.
    while isa_abs(lhs) or isa_abs(rhs):
        lhs = bohm.unabstract(lhs)
        rhs = bohm.unabstract(rhs)
    assert lhs is not rhs, lhs

    # Destructure APP.
    lhs_head, lhs_args = bohm.unapply(lhs)
    rhs_head, rhs_args = bohm.unapply(rhs)

    # Distinguish solvable terms.
    if isa_ivar(lhs_head) and isa_ivar(rhs_head):
        if lhs_head is not rhs_head or len(lhs_args) != len(rhs_args):
            return False
        for eqn in zip(lhs_args, rhs_args):
            lhs_arg, rhs_arg = eqn
            theory.assume_equal(lhs_arg, rhs_arg)
        return True

    # Distinguish atoms from local variables.
    if isa_ivar(lhs_head) and (rhs is TOP or rhs is BOT):
        return False
    if isa_ivar(rhs_head) and (lhs is TOP or lhs is BOT):
        return False

    # Unfold NVARs.
    assert is_unfoldable(lhs) or is_unfoldable(rhs), (lhs, rhs)
    if is_unfoldable(lhs):
        lhs = unfold(system, lhs)
        theory.assume_equal(lhs, rhs)
    if is_unfoldable(rhs):
        rhs = unfold(system, rhs)
        theory.assume_equal(lhs, rhs)
    return True


def try_decide_equal(system, lhs, rhs):
    """Incomplete unsound decision procedure for extensional equality.

    This attempts to adapt Huet's decision procedure for extensional equality
    from rational Bohm trees to arbitrary systems of combinators.

    Does not handle JOIN.
    Does not handle nonterminating terms.
    Does not handle least fixed points defined via mutual recursion.
    """
    assert isinstance(system, System), system
    assert is_valid_body(lhs), lhs
    assert is_valid_body(rhs), rhs

    theory = Theory()
    theory.assume_equal(lhs, rhs)
    while theory.has_assumptions():
        lhs, rhs = theory.pop()
        if not try_match_equal(system, theory, lhs, rhs):
            return False
    return True
