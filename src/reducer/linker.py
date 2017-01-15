from pomagma.compiler.util import memoize_args
from pomagma.reducer import lib
from pomagma.reducer.sugar import as_code
from pomagma.reducer.syntax import (ABS, APP, JOIN, QUOTE, free_vars, isa_abs,
                                    isa_app, isa_atom, isa_ivar, isa_join,
                                    isa_nvar, isa_quote)


@memoize_args
def _substitute(var, defn, body):
    if isa_atom(body) or isa_ivar(body):
        return body
    elif isa_nvar(body):
        if body is var:
            return defn
        else:
            return body
    elif isa_abs(body):
        arg = _substitute(var, defn, body[1])
        return ABS(arg)
    elif isa_app(body):
        lhs = _substitute(var, defn, body[1])
        rhs = _substitute(var, defn, body[2])
        return APP(lhs, rhs)
    elif isa_join(body):
        lhs = _substitute(var, defn, body[1])
        rhs = _substitute(var, defn, body[2])
        return JOIN(lhs, rhs)
    elif isa_quote(body):
        arg = _substitute(var, defn, body[1])
        return QUOTE(arg)
    else:
        raise ValueError(body)


def substitute(var, defn, body):
    """Eagerly substitute a de Bruijn-closed term for a nominal variable."""
    if not isa_nvar(var):
        raise ValueError('Expected a nominal variable, got {}'.format(var))
    if any(map(isa_ivar, free_vars(defn))):
        raise ValueError('Definition is not closed: {}'.format(defn))
    return _substitute(var, defn, body)


def bind(code, var):
    assert var[1].startswith('lib.')
    name = var[1][4:]
    defn = getattr(lib, name)  # raises AttributeError if not found.
    return substitute(var, as_code(defn), code)


def link(code):
    code = as_code(code)
    free = free_vars(code)
    to_bind = sorted(var for var in free if var[1].startswith('lib.'))
    for var in to_bind:
        code = bind(code, var)

    return code
