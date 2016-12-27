"""Conversions to combinatory logic, a la Curry."""

__all__ = ['try_abstract', 'abstract', 'compile_']

from pomagma.compiler.util import memoize_args
from pomagma.reducer.syntax import (APP, BOT, JOIN, QUOTE, TOP, B, C, I, K, S,
                                    is_app, is_atom, is_fun, is_join, is_nvar,
                                    is_quote)
from pomagma.util import TODO


# ----------------------------------------------------------------------------
# Abstraction

@memoize_args
def try_abstract(var, body):
    """Returns \\var.body if var occurs in body, else None."""
    if not is_nvar(var):
        raise NotImplementedError('Only variables can be abstracted')
    if body is var:
        return I  # Rule I
    elif is_app(body):
        lhs = body[1]
        rhs = body[2]
        lhs_abs = try_abstract(var, lhs)
        rhs_abs = try_abstract(var, rhs)
        if lhs_abs is None:
            if rhs_abs is None:
                return None  # Rule K
            elif rhs_abs is I:
                return lhs  # Rule eta
            else:
                return APP(APP(B, lhs), rhs_abs)  # Rule B
        else:
            if rhs_abs is None:
                return APP(APP(C, lhs_abs), rhs)  # Rule C
            else:
                return APP(APP(S, lhs_abs), rhs_abs)  # Rule S
    elif is_join(body):
        lhs = body[1]
        rhs = body[2]
        lhs_abs = try_abstract(var, lhs)
        rhs_abs = try_abstract(var, rhs)
        if lhs_abs is None:
            if rhs_abs is None:
                return None  # Rule K
            else:
                return JOIN(APP(K, lhs), rhs_abs)  # Rule JOIN-K
        else:
            if rhs_abs is None:
                return JOIN(lhs_abs, APP(K, rhs))  # Rule JOIN-K
            else:
                return JOIN(lhs_abs, rhs_abs)  # Rule JOIN
    else:
        return None  # Rule K


def abstract(var, body):
    """APP,JOIN,TOP,BOT,I,K,B,C,S,eta-abstraction algorithm."""
    result = try_abstract(var, body)
    if result is not None:
        return result
    elif body in (TOP, BOT):
        return body  # Rules TOP, BOT
    else:
        return APP(K, body)  # Rule K


def qabstract(var, body):
    TODO('Support quoted recursion')


# ----------------------------------------------------------------------------
# Symbolic compiler : FUN -> I,K,B,C,S

def compile_(code):
    if is_atom(code):
        return code
    elif is_nvar(code):
        return code
    elif is_app(code):
        x = compile_(code[1])
        y = compile_(code[2])
        return APP(x, y)
    elif is_join(code):
        x = compile_(code[1])
        y = compile_(code[2])
        return JOIN(x, y)
    elif is_quote(code):
        arg = compile_(code[1])
        return QUOTE(arg)
    elif is_fun(code):
        var = code[1]
        body = compile_(code[2])
        return abstract(var, body)
    else:
        raise ValueError('Cannot compile_: {}'.format(code))
