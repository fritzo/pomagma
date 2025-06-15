"""Nominal lambda-calculus a la Alonzo Church."""

from pomagma.compiler.util import memoize_arg, memoize_args, unique_result
from pomagma.reducer.syntax import (
    ABS,
    APP,
    FUN,
    IVAR,
    JOIN,
    NVAR,
    QUOTE,
    Term,
    is_abs,
    is_app,
    is_atom,
    is_fun,
    is_ivar,
    is_join,
    is_nvar,
    is_quote,
    sexpr_print,
)

pretty = sexpr_print


@memoize_arg
@unique_result
def nominal_vars(term):
    """Find all bound and free nominal variables."""
    if not isinstance(term, Term):
        raise ValueError(term)
    if is_nvar(term):
        return frozenset([term])
    if is_ivar(term) or is_atom(term):
        return frozenset()
    if is_abs(term) or is_quote(term):
        return nominal_vars(term[1])
    if is_app(term) or is_join(term) or is_fun(term):
        return nominal_vars(term[1]) | nominal_vars(term[2])
    raise ValueError(pretty(term))


VARS = list(map(NVAR, "abcdefghijklmnopqrstuvwxyz"))


def iter_fresh(term):
    avoid = nominal_vars(term)
    for var in VARS:
        if var not in avoid:
            yield var
    raise NotImplementedError("Too many bound variables")


@memoize_args
def _nominalize(term, var, rank):
    if is_ivar(term):
        if term[1] < rank:
            return term
        if term[1] == rank:
            return var
        return IVAR(term[1] - 1)
    if is_atom(term) or is_nvar(term):
        return term
    if is_abs(term):
        body = _nominalize(term[1], var, rank + 1)
        return ABS(body)
    if is_fun(term):
        body = _nominalize(term[2], var, rank)
        return FUN(term[1], body)
    if is_app(term):
        lhs = _nominalize(term[1], var, rank)
        rhs = _nominalize(term[2], var, rank)
        return APP(lhs, rhs)
    if is_join(term):
        lhs = _nominalize(term[1], var, rank)
        rhs = _nominalize(term[2], var, rank)
        return JOIN(lhs, rhs)
    if is_quote(term):
        body = _nominalize(term[1], var, rank)
        return QUOTE(body)
    return ValueError(term)


def convert(term, fresh=None):
    """Replace all bound ABS,IVAR pairs with FUN,VAR pairs."""
    if fresh is None:
        fresh = iter_fresh(term)
    if is_atom(term) or is_nvar(term) or is_ivar(term):
        return term
    if is_abs(term):
        var = next(fresh)
        body = _nominalize(term[1], var, 0)
        body = convert(body, fresh)
        return FUN(var, body)
    if is_fun(term):
        body = convert(term[2], fresh)
        return FUN(term[1], body)
    if is_app(term):
        lhs = convert(term[1], fresh)
        rhs = convert(term[2], fresh)
        return APP(lhs, rhs)
    if is_join(term):
        lhs = convert(term[1], fresh)
        rhs = convert(term[2], fresh)
        return JOIN(lhs, rhs)
    if is_quote(term):
        body = convert(term[1], fresh)
        return QUOTE(body)
    raise ValueError(term)
