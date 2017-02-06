from collections import OrderedDict

from pomagma.compiler.util import memoize_arg
from pomagma.reducer import bohm
from pomagma.reducer.syntax import (NVAR, Term, free_vars, is_closed, isa_abs,
                                    isa_app, isa_atom, isa_ivar, isa_join,
                                    isa_nvar, iter_join, TOP, BOT)


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
        return all(is_abs_free(part) for part in iter_join(term))
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
    if not is_closed(term) or not bohm.is_normal(term):
        return False
    if term is TOP or term is BOT:
        return False
    while isa_abs(term):
        term = term[1]
    return is_abs_free(term)


class System(object):
    """System of mutually recursive combinators."""

    def __init__(self, **defs):
        self._defs = OrderedDict  # : NVAR -> closed Term
        for name, body in defs.iteritems():
            self.define(NVAR(name), body)
        assert self.is_closed()

    def define(self, name, body):
        assert isinstance(name, str)
        assert isinstance(body, Term)
        assert is_valid_body(body)
        self._defs[NVAR(name)] = body

    def __getitem__(self, var):
        assert isa_nvar(var)
        return self._defs[var]

    def __iter__(self):
        return self._defs.iteritems()

    def __repr__(self):
        defs = [
            '{}={}'.format(var[1], body)
            for var, body in self._defs.iteritems()
        ]
        return 'System(\n    {}\n)'.format('\n,    '.join(defs))

    __str__ = __repr__

    def is_closed(self):
        """Whether all free NVARs are defined."""
        return all(
            var in self._defs
            for body in self._defs.itervalues()
            for var in free_vars(body)
        )


@memoize_arg
def is_unfoldable(body):
    assert isinstance(body, Term)
    assert is_valid_body(body)
    if isa_join(body):
        return any(is_unfoldable(term) for term in iter_join(body))
    while isa_abs(body):
        body = body[1]
    while isa_app(body):
        body = body[1]
    return isa_nvar(body)


def unfold(system, body):
    if isa_atom(body) or isa_ivar(body):
        return body
    if isa_nvar(body):
        return system[body]

    # Get a linear normal form.
    if isa_app(body):
        body = bohm.app(unfold(body[1]), body[2])  # Only unfold head.
    elif isa_abs(body):
        body = bohm.abstract(unfold(body[1]))
    elif isa_join(body):
        body = bohm.join(unfold(part) for part in iter_join(body))
    else:
        raise ValueError(body)

    # Reduce.
    return bohm.reduce(body, budget=1234567890)


def try_beta_step(system):
    assert isinstance(system, System)
    for var, body in system:
        if is_unfoldable(body):
            unfolded = unfold(system, body)
            system.define(var[1], unfolded)
            return True
    return False
