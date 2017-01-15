"""Nominal lambda-calculus a la Alonzo Church."""

from pomagma.compiler.util import memoize_arg, memoize_args, unique_result
from pomagma.reducer.syntax import (ABS, APP, FUN, IVAR, JOIN, NVAR, QUOTE,
                                    isa_abs, isa_app, isa_atom, isa_code,
                                    isa_fun, isa_ivar, isa_join, isa_nvar,
                                    isa_quote, sexpr_print)

pretty = sexpr_print


@memoize_arg
@unique_result
def nominal_vars(code):
    """Find all bound and free nominal variables."""
    if not isa_code(code):
        raise ValueError(code)
    elif isa_nvar(code):
        return frozenset([code])
    elif isa_ivar(code) or isa_atom(code):
        return frozenset()
    elif isa_abs(code) or isa_quote(code):
        return nominal_vars(code[1])
    elif isa_app(code) or isa_join(code) or isa_fun(code):
        return nominal_vars(code[1]) | nominal_vars(code[2])
    else:
        raise ValueError(pretty(code))


VARS = map(NVAR, 'abcdefghijklmnopqrstuvwxyz')


def iter_fresh(code):
    avoid = nominal_vars(code)
    for var in VARS:
        if var not in avoid:
            yield var
    raise NotImplementedError('Too many bound variables')


@memoize_args
def _nominalize(code, var, rank):
    if isa_ivar(code):
        if code[1] < rank:
            return code
        elif code[1] == rank:
            return var
        else:
            return IVAR(code[1] - 1)
    elif isa_atom(code) or isa_nvar(code):
        return code
    elif isa_abs(code):
        body = _nominalize(code[1], var, rank + 1)
        return ABS(body)
    elif isa_fun(code):
        body = _nominalize(code[2], var, rank)
        return FUN(code[1], body)
    elif isa_app(code):
        lhs = _nominalize(code[1], var, rank)
        rhs = _nominalize(code[2], var, rank)
        return APP(lhs, rhs)
    elif isa_join(code):
        lhs = _nominalize(code[1], var, rank)
        rhs = _nominalize(code[2], var, rank)
        return JOIN(lhs, rhs)
    elif isa_quote(code):
        body = _nominalize(code[1], var, rank)
        return QUOTE(body)
    else:
        return ValueError(code)


def convert(code, fresh=None):
    """Replace all bound ABS,IVAR pairs with FUN,VAR pairs."""
    if fresh is None:
        fresh = iter_fresh(code)
    if isa_atom(code) or isa_nvar(code) or isa_ivar(code):
        return code
    elif isa_abs(code):
        var = next(fresh)
        body = _nominalize(code[1], var, 0)
        body = convert(body, fresh)
        return FUN(var, body)
    elif isa_fun(code):
        body = convert(code[2], fresh)
        return FUN(code[1], body)
    elif isa_app(code):
        lhs = convert(code[1], fresh)
        rhs = convert(code[2], fresh)
        return APP(lhs, rhs)
    elif isa_join(code):
        lhs = convert(code[1], fresh)
        rhs = convert(code[2], fresh)
        return JOIN(lhs, rhs)
    elif isa_quote(code):
        body = convert(code[1], fresh)
        return QUOTE(body)
    else:
        raise ValueError(code)
