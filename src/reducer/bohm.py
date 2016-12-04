"""Eager linear reduction of linear Bohm trees.

This sketches a method of eagerly linearly reducing de Bruijn indexed codes so
that the only codes built are linear Bohm trees. This contrasts older
implementations by entirely avoiding use of combinators. The original
motivation for avoiding combinators was to make it easier to implement
try_decide_less in engines.continuation.

CHANGELOG
2016-12-04 Initial prototype.
"""

from pomagma.compiler.util import memoize_args
from pomagma.reducer.code import (
    TOP, BOT, IVAR, APP, JOIN, ABS,
    is_atom, is_nvar, is_ivar, is_app, is_abs, is_join, is_quote,
)
from pomagma.util import TODO


@memoize_args
def increment_rank(code, min_rank):
    if is_nvar(code) or is_atom(code) or is_quote(code):
        return code
    elif is_ivar(code):
        rank = code[1]
        return IVAR(rank + 1) if rank >= min_rank else code
    elif is_abs(code):
        return ABS(increment_rank(code, min_rank + 1))
    elif is_app(code):
        lhs = increment_rank(code[1], min_rank)
        rhs = increment_rank(code[2], min_rank)
        return APP(lhs, rhs)
    elif is_join(code):
        lhs = increment_rank(code[1], min_rank)
        rhs = increment_rank(code[2], min_rank)
        return JOIN(lhs, rhs)
    else:
        raise ValueError(code)


@memoize_args
def try_decrement_rank(code, min_rank):
    if is_nvar(code) or is_atom(code) or is_quote(code):
        return code
    elif is_ivar(code):
        rank = code[1]
        if rank == 0:
            return None
        return IVAR(rank - 1)
    elif is_abs(code):
        return ABS(decrement_rank(code, min_rank + 1))
    elif is_app(code):
        lhs = decrement_rank(code[1], min_rank)
        rhs = decrement_rank(code[2], min_rank)
        return APP(lhs, rhs)
    elif is_join(code):
        lhs = decrement_rank(code[1], min_rank)
        rhs = decrement_rank(code[2], min_rank)
        return JOIN(lhs, rhs)
    else:
        raise ValueError(code)


def decrement_rank(code, min_rank):
    result = try_decrement_rank(code, min_rank)
    if result is None:
        raise ValueError(code)
    return result


def is_const(code):
    return try_decrement_rank(code, 0) is None


# TODO replace subs by a linear define(-,-,-), and simplify app(-,-).
@memoize_args
def subs(body, value, rank):
    if is_ivar(body):
        return value if body[1] == rank else body
    elif is_atom(body) or is_nvar(body) or is_quote(body):
        return body
    elif is_app(body):
        lhs = subs(body[1], value, rank)
        rhs = subs(body[2], value, rank)
        return app(lhs, rhs)
    elif is_abs(body):
        return abstract(subs(body, increment_rank(value, 0), rank + 1))
    elif is_join(body):
        lhs = subs(body[1], value, rank)
        rhs = subs(body[2], value, rank)
        return join(lhs, rhs)
    else:
        raise ValueError(body)


@memoize_args
def app(fun, key):
    """Apply function to argument and linearly reduce."""
    if fun is TOP or fun is BOT:
        return fun
    elif is_nvar(fun) or is_ivar(fun) or is_quote(fun):
        return APP(fun, key)
    elif is_app(fun):
        # TODO try to reduce LESS x y.
        return APP(fun, key)
    elif is_join(fun):
        lhs = app(fun[1], key)
        rhs = app(fun[2], key)
        return join(lhs, rhs)
    elif is_abs(fun):
        # Linearly reduce.
        body = fun[1]
        if is_ivar(body):
            rank = body[1]
            return key if rank == 0 else IVAR(rank - 1)
        elif is_app(body):
            lhs = body[1]
            rhs = body[2]
            if is_cheap_to_copy(key) or is_const(lhs) or is_const(rhs):
                return subs(body, key, 0)
            else:
                return app(fun, key)
        else:
            raise ValueError(body)
    else:
        raise ValueError(fun)


@memoize_args
def abstract(body):
    """Abstract one de Bruijn var and eta-contract."""
    if body is TOP or body is BOT:
        return body
    elif is_join(body):
        lhs = abstract(body[1])
        rhs = abstract(body[2])
        return join(lhs, rhs)
    elif is_app(body) and body[2] is IVAR(0) and is_const(body[1]):
        # Eta contract.
        return decrement_rank(body[1])
    else:
        return ABS(body)


@memoize_args
def join(lhs, rhs):
    codes = set()
    for term in iter_join(lhs):
        codes.add(term)
    for term in iter_join(rhs):
        codes.add(term)
    return join_codes(codes)


def iter_join(code):
    if is_join(code):
        for term in iter_join(code[1]):
            yield term
        for term in iter_join(code[2]):
            yield term
    elif code is not BOT:
        yield code


def join_codes(codes):
    if not isinstance(codes, set):
        raise ValueError(codes)
    TODO('adapt logic from engines.de_bruijn')


def is_cheap_to_copy(code):
    TODO()
