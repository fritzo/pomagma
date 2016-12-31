"""Nominal lambda-calculus a la Alonzo Church."""

from pomagma.compiler.util import memoize_arg, memoize_args, unique
from pomagma.reducer.syntax import (ABS, APP, FUN, IVAR, JOIN, NVAR, QUOTE,
                                    is_abs, is_app, is_atom, is_code, is_fun,
                                    is_ivar, is_join, is_nvar, is_quote,
                                    sexpr_print)

pretty = sexpr_print


@memoize_arg
@unique
def nominal_vars(code):
    """Find all bound and free nominal variables."""
    if not is_code(code):
        raise ValueError(code)
    elif is_nvar(code):
        return frozenset([code])
    elif is_ivar(code) or is_atom(code):
        return frozenset()
    elif is_abs(code) or is_quote(code):
        return nominal_vars(code[1])
    elif is_app(code) or is_join(code) or is_fun(code):
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
    if is_ivar(code):
        if code[1] < rank:
            return code
        elif code[1] == rank:
            return var
        else:
            return IVAR(code[1] - 1)
    elif is_atom(code) or is_nvar(code):
        return code
    elif is_abs(code):
        body = _nominalize(code[1], var, rank + 1)
        return ABS(body)
    elif is_fun(code):
        body = _nominalize(code[2], var, rank)
        return FUN(code[1], body)
    elif is_app(code):
        lhs = _nominalize(code[1], var, rank)
        rhs = _nominalize(code[2], var, rank)
        return APP(lhs, rhs)
    elif is_join(code):
        lhs = _nominalize(code[1], var, rank)
        rhs = _nominalize(code[2], var, rank)
        return JOIN(lhs, rhs)
    elif is_quote(code):
        body = _nominalize(code[1], var, rank)
        return QUOTE(body)
    else:
        return ValueError(code)


def convert(code, fresh=None):
    """Replace all bound ABS,IVAR pairs with FUN,VAR pairs."""
    if fresh is None:
        fresh = iter_fresh(code)
    if is_atom(code) or is_nvar(code) or is_ivar(code):
        return code
    elif is_abs(code):
        var = next(fresh)
        body = _nominalize(code[1], var, 0)
        body = convert(body, fresh)
        return FUN(var, body)
    elif is_fun(code):
        body = convert(code[2], fresh)
        return FUN(code[1], body)
    elif is_app(code):
        lhs = convert(code[1], fresh)
        rhs = convert(code[2], fresh)
        return APP(lhs, rhs)
    elif is_join(code):
        lhs = convert(code[1], fresh)
        rhs = convert(code[2], fresh)
        return JOIN(lhs, rhs)
    elif is_quote(code):
        body = convert(code[1], fresh)
        return QUOTE(body)
    else:
        raise ValueError(code)
