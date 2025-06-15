from pomagma.compiler.util import memoize_args
from pomagma.reducer import lib
from pomagma.reducer.sugar import as_term
from pomagma.reducer.syntax import (
    ABS,
    APP,
    JOIN,
    QUOTE,
    free_vars,
    is_abs,
    is_app,
    is_atom,
    is_ivar,
    is_join,
    is_nvar,
    is_quote,
)


@memoize_args
def _substitute(var, defn, body):
    if is_atom(body) or is_ivar(body):
        return body
    if is_nvar(body):
        if body is var:
            return defn
        return body
    if is_abs(body):
        arg = _substitute(var, defn, body[1])
        return ABS(arg)
    if is_app(body):
        lhs = _substitute(var, defn, body[1])
        rhs = _substitute(var, defn, body[2])
        return APP(lhs, rhs)
    if is_join(body):
        lhs = _substitute(var, defn, body[1])
        rhs = _substitute(var, defn, body[2])
        return JOIN(lhs, rhs)
    if is_quote(body):
        arg = _substitute(var, defn, body[1])
        return QUOTE(arg)
    raise ValueError(body)


def substitute(var, defn, body):
    """Eagerly substitute a de Bruijn-closed term for a nominal variable."""
    if not is_nvar(var):
        raise ValueError(f"Expected a nominal variable, got {var}")
    if any(map(is_ivar, free_vars(defn))):
        raise ValueError(f"Definition is not closed: {defn}")
    return _substitute(var, defn, body)


def bind(term, var):
    assert var[1].startswith("lib.")
    name = var[1][4:]
    defn = getattr(lib, name)  # raises AttributeError if not found.
    return substitute(var, as_term(defn), term)


def link(term):
    term = as_term(term)
    free = free_vars(term)
    to_bind = sorted(var for var in free if var[1].startswith("lib."))
    for var in to_bind:
        term = bind(term, var)

    return term
