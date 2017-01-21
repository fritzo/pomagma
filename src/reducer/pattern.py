from pomagma.reducer.bohm import decrement_rank
from pomagma.reducer.syntax import (IVAR_0, Term, free_vars, isa_abs, isa_app,
                                    isa_atom, isa_ivar, isa_join, isa_nvar,
                                    isa_quote)


class NoMatch(Exception):
    pass


def _match(pattern, term, defs, rank):
    if isa_nvar(pattern):
        for _ in xrange(rank):
            if IVAR_0 in free_vars(term):
                raise NoMatch
            term = decrement_rank(term)
        if defs.setdefault(pattern, term) is not term:
            raise NoMatch
    elif isa_atom(pattern) or isa_ivar(pattern):
        if pattern is not term:
            raise NoMatch
    elif isa_abs(pattern):
        if not isa_abs(term):
            raise NoMatch
        _match(pattern[1], term[1], defs, rank + 1)
    elif isa_app(pattern):
        if not isa_app(term):
            raise NoMatch
        _match(pattern[1], term[1], defs, rank)
        _match(pattern[2], term[2], defs, rank)
    elif isa_join(pattern):
        if not isa_join(term):
            raise NoMatch
        _match(pattern[1], term[1], defs, rank)
        _match(pattern[2], term[2], defs, rank)
    elif isa_quote(pattern):
        if not isa_quote(term):
            raise NoMatch
        _match(pattern[1], term[1], defs, rank)
    else:
        raise ValueError(pattern)


def match(pattern, term):
    """Try to match a pattern.

    Args:
      pattern : a term with optional free nominal variables
      term : a term

    Returns:
      None if no match was found; otherwise a dict from NVARs to values.

    """
    assert isinstance(pattern, Term), pattern
    assert isinstance(term, Term), term
    defs = {}
    try:
        _match(pattern, term, defs, 0)
    except NoMatch:
        return None
    return defs
