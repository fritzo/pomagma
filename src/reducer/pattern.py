from pomagma.reducer.bohm import decrement_rank
from pomagma.reducer.syntax import (IVAR_0, Code, free_vars, isa_abs, isa_app,
                                    isa_atom, isa_ivar, isa_join, isa_nvar,
                                    isa_quote)


class NoMatch(Exception):
    pass


def _match(pattern, code, defs, rank):
    if isa_nvar(pattern):
        for _ in xrange(rank):
            if IVAR_0 in free_vars(code):
                raise NoMatch
            code = decrement_rank(code)
        if defs.setdefault(pattern, code) is not code:
            raise NoMatch
    elif isa_atom(pattern) or isa_ivar(pattern):
        if pattern is not code:
            raise NoMatch
    elif isa_abs(pattern):
        if not isa_abs(code):
            raise NoMatch
        _match(pattern[1], code[1], defs, rank + 1)
    elif isa_app(pattern):
        if not isa_app(code):
            raise NoMatch
        _match(pattern[1], code[1], defs, rank)
        _match(pattern[2], code[2], defs, rank)
    elif isa_join(pattern):
        if not isa_join(code):
            raise NoMatch
        _match(pattern[1], code[1], defs, rank)
        _match(pattern[2], code[2], defs, rank)
    elif isa_quote(pattern):
        if not isa_quote(code):
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
    assert isinstance(pattern, Code), pattern
    assert isinstance(code, Code), code
    defs = {}
    try:
        _match(pattern, code, defs, 0)
    except NoMatch:
        return None
    return defs
