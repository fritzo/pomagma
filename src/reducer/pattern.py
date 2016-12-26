from pomagma.reducer.bohm import decrement_rank
from pomagma.reducer.syntax import (IVAR_0, free_vars, is_abs, is_app, is_atom,
                                    is_code, is_ivar, is_join, is_nvar,
                                    is_quote)


class NoMatch(Exception):
    pass


def _match(pattern, code, defs, rank):
    if is_nvar(pattern):
        for _ in xrange(rank):
            if IVAR_0 in free_vars(code):
                raise NoMatch
            code = decrement_rank(code)
        if defs.setdefault(pattern, code) is not code:
            raise NoMatch
    elif is_atom(pattern) or is_ivar(pattern):
        if pattern is not code:
            raise NoMatch
    elif is_abs(pattern):
        if not is_abs(code):
            raise NoMatch
        _match(pattern[1], code[1], defs, rank + 1)
    elif is_app(pattern):
        if not is_app(code):
            raise NoMatch
        _match(pattern[1], code[1], defs, rank)
        _match(pattern[2], code[2], defs, rank)
    elif is_join(pattern):
        if not is_join(code):
            raise NoMatch
        _match(pattern[1], code[1], defs, rank)
        _match(pattern[2], code[2], defs, rank)
    elif is_quote(pattern):
        if not is_quote(code):
            raise NoMatch
        _match(pattern[1], code[1], defs, rank)
    else:
        raise ValueError(pattern)


def match(pattern, code):
    """Try to match a pattern.

    Args:
      pattern : a code with optional free nominal variables
      code : a code

    Returns:
      None if no match was found; otherwise a dict from NVARs to values.

    """
    assert is_code(pattern), pattern
    assert is_code(code), code
    defs = {}
    try:
        _match(pattern, code, defs, 0)
    except NoMatch:
        return None
    return defs
