from pomagma.reducer.bohm import decrement_rank
from pomagma.reducer.syntax import (
    IVAR_0,
    Term,
    free_vars,
    is_abs,
    is_app,
    is_atom,
    is_ivar,
    is_join,
    is_nvar,
    is_quote,
)


class NoMatch(Exception):
    pass


def _match(pattern, term, defs, rank):
    if is_nvar(pattern):
        for _ in range(rank):
            if IVAR_0 in free_vars(term):
                raise NoMatch
            term = decrement_rank(term)
        if defs.setdefault(pattern, term) is not term:
            raise NoMatch
    elif is_atom(pattern) or is_ivar(pattern):
        if pattern is not term:
            raise NoMatch
    elif is_abs(pattern):
        if not is_abs(term):
            raise NoMatch
        _match(pattern[1], term[1], defs, rank + 1)
    elif is_app(pattern):
        if not is_app(term):
            raise NoMatch
        _match(pattern[1], term[1], defs, rank)
        _match(pattern[2], term[2], defs, rank)
    elif is_join(pattern):
        if not is_join(term):
            raise NoMatch
        _match(pattern[1], term[1], defs, rank)
        _match(pattern[2], term[2], defs, rank)
    elif is_quote(pattern):
        if not is_quote(term):
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
