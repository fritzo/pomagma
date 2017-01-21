"""Nominal lambda-calculus a la Alonzo Church."""

from pomagma.compiler.util import memoize_arg, memoize_args, unique_result
from pomagma.reducer.syntax import (ABS, APP, FUN, IVAR, JOIN, NVAR, QUOTE,
                                    Term, isa_abs, isa_app, isa_atom, isa_fun,
                                    isa_ivar, isa_join, isa_nvar, isa_quote,
                                    sexpr_print)

pretty = sexpr_print


@memoize_arg
@unique_result
def nominal_vars(term):
    """Find all bound and free nominal variables."""
    if not isinstance(term, Term):
        raise ValueError(term)
    elif isa_nvar(term):
        return frozenset([term])
    elif isa_ivar(term) or isa_atom(term):
        return frozenset()
    elif isa_abs(term) or isa_quote(term):
        return nominal_vars(term[1])
    elif isa_app(term) or isa_join(term) or isa_fun(term):
        return nominal_vars(term[1]) | nominal_vars(term[2])
    else:
        raise ValueError(pretty(term))


VARS = map(NVAR, 'abcdefghijklmnopqrstuvwxyz')


def iter_fresh(term):
    avoid = nominal_vars(term)
    for var in VARS:
        if var not in avoid:
            yield var
    raise NotImplementedError('Too many bound variables')


@memoize_args
def _nominalize(term, var, rank):
    if isa_ivar(term):
        if term[1] < rank:
            return term
        elif term[1] == rank:
            return var
        else:
            return IVAR(term[1] - 1)
    elif isa_atom(term) or isa_nvar(term):
        return term
    elif isa_abs(term):
        body = _nominalize(term[1], var, rank + 1)
        return ABS(body)
    elif isa_fun(term):
        body = _nominalize(term[2], var, rank)
        return FUN(term[1], body)
    elif isa_app(term):
        lhs = _nominalize(term[1], var, rank)
        rhs = _nominalize(term[2], var, rank)
        return APP(lhs, rhs)
    elif isa_join(term):
        lhs = _nominalize(term[1], var, rank)
        rhs = _nominalize(term[2], var, rank)
        return JOIN(lhs, rhs)
    elif isa_quote(term):
        body = _nominalize(term[1], var, rank)
        return QUOTE(body)
    else:
        return ValueError(term)


def convert(term, fresh=None):
    """Replace all bound ABS,IVAR pairs with FUN,VAR pairs."""
    if fresh is None:
        fresh = iter_fresh(term)
    if isa_atom(term) or isa_nvar(term) or isa_ivar(term):
        return term
    elif isa_abs(term):
        var = next(fresh)
        body = _nominalize(term[1], var, 0)
        body = convert(body, fresh)
        return FUN(var, body)
    elif isa_fun(term):
        body = convert(term[2], fresh)
        return FUN(term[1], body)
    elif isa_app(term):
        lhs = convert(term[1], fresh)
        rhs = convert(term[2], fresh)
        return APP(lhs, rhs)
    elif isa_join(term):
        lhs = convert(term[1], fresh)
        rhs = convert(term[2], fresh)
        return JOIN(lhs, rhs)
    elif isa_quote(term):
        body = convert(term[1], fresh)
        return QUOTE(body)
    else:
        raise ValueError(term)
