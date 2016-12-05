"""Eager linear reduction of linear Bohm trees.

This sketches a method of eagerly linearly reducing de Bruijn indexed codes so
that the only codes built are linear Bohm trees. This contrasts older
implementations by entirely avoiding use of combinators. The original
motivation for avoiding combinators was to make it easier to implement
try_decide_less in engines.continuation.

CHANGELOG
2016-12-04 Initial prototype.
"""

from pomagma.compiler.util import memoize_arg, memoize_args
from pomagma.reducer.code import (
    TOP, BOT, IVAR, APP, ABS, JOIN, QUOTE,
    is_code, is_nvar, is_ivar, is_app, is_abs, is_join, is_quote,
    complexity,
)
from pomagma.util import TODO


# ----------------------------------------------------------------------------
# Functional programming

@memoize_args
def increment_rank(code, min_rank):
    if code is TOP:
        return code
    elif code is BOT:
        return code
    elif is_nvar(code):
        return code
    elif is_ivar(code):
        rank = code[1]
        return IVAR(rank + 1) if rank >= min_rank else code
    elif is_abs(code):
        return ABS(increment_rank(code[1], min_rank + 1))
    elif is_app(code):
        lhs = increment_rank(code[1], min_rank)
        rhs = increment_rank(code[2], min_rank)
        return APP(lhs, rhs)
    elif is_join(code):
        lhs = increment_rank(code[1], min_rank)
        rhs = increment_rank(code[2], min_rank)
        return JOIN(lhs, rhs)
    elif is_quote(code):
        return code
    else:
        raise ValueError(code)


class CannotDecrementRank(Exception):
    pass


@memoize_args
def _try_decrement_rank(code, min_rank):
    if code is TOP:
        return code
    elif code is BOT:
        return code
    elif is_nvar(code) or is_quote(code):
        return code
    elif is_ivar(code):
        rank = code[1]
        if rank < min_rank:
            return code
        elif rank == min_rank:
            raise CannotDecrementRank
        return IVAR(rank - 1)
    elif is_app(code):
        lhs = _try_decrement_rank(code[1], min_rank)
        rhs = _try_decrement_rank(code[2], min_rank)
        return APP(lhs, rhs)
    elif is_abs(code):
        return ABS(_try_decrement_rank(code[1], min_rank + 1))
    elif is_join(code):
        lhs = _try_decrement_rank(code[1], min_rank)
        rhs = _try_decrement_rank(code[2], min_rank)
        return JOIN(lhs, rhs)
    else:
        raise ValueError(code)


def decrement_rank(code):
    try:
        return _try_decrement_rank(code, 0)
    except CannotDecrementRank:
        raise ValueError(code)


def is_const(code, rank=0):
    try:
        _try_decrement_rank(code, rank)
    except CannotDecrementRank:
        return False
    return True


def is_cheap_to_copy(code):
    """Guard to prevent nontermination.

    This accounts for the worst case of complexity 3:

        ABS(APP(IVAR(0), IVAR(0)))
    """
    return complexity(code) <= 3


@memoize_args
def substitute(body, value, rank):
    """Linearly substitute value for IVAR(rank) in body."""
    if body is TOP:
        return body
    elif body is BOT:
        return body
    elif is_nvar(body):
        return body
    elif is_ivar(body):
        return value if body[1] == rank else body
    elif is_app(body):
        lhs = body[1]
        rhs = body[2]
        if (is_cheap_to_copy(value) or is_const(lhs, rank) or
                is_const(rhs, rank)):
            lhs = substitute(lhs, value, rank)
            rhs = substitute(rhs, value, rank)
            return app(lhs, rhs)
        else:
            return APP(ABS(body), value)
    elif is_abs(body):
        return abstract(substitute(body, increment_rank(value, 0), rank + 1))
    elif is_join(body):
        lhs = substitute(body[1], value, rank)
        rhs = substitute(body[2], value, rank)
        return join(lhs, rhs)
    elif is_quote(body):
        return body
    else:
        raise ValueError(body)


@memoize_args
def app(fun, key):
    """Apply function to argument and linearly reduce."""
    if fun is TOP:
        return fun
    elif fun is BOT:
        return fun
    elif is_nvar(fun):
        return APP(fun, key)
    elif is_ivar(fun):
        return APP(fun, key)
    elif is_app(fun):
        # TODO try to reduce LESS x y.
        return APP(fun, key)
    elif is_abs(fun):
        body = fun[1]
        return substitute(body, key)
    elif is_join(fun):
        lhs = app(fun[1], key)
        rhs = app(fun[2], key)
        return join(lhs, rhs)
    elif is_quote(fun):
        return APP(fun, key)
    else:
        raise ValueError(fun)


@memoize_args
def abstract(body):
    """Abstract one de Bruijn var and eta-contract."""
    if body is TOP:
        return body
    elif body is BOT:
        return body
    elif is_nvar(body):
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


# ----------------------------------------------------------------------------
# Scott ordering

def iter_join(code):
    if is_join(code):
        for term in iter_join(code[1]):
            yield term
        for term in iter_join(code[2]):
            yield term
    elif code is not BOT:
        yield code


@memoize_args
def join(lhs, rhs):
    """Join two codes, modulo linear Scott ordering."""

    # Destructure all JOIN terms.
    codes = set()
    for term in iter_join(lhs):
        codes.add(term)
    for term in iter_join(rhs):
        codes.add(term)
    if not codes:
        return BOT
    if len(codes) == 1:
        return next(iter(codes))

    # Filter out strictly dominated codes.
    filtered_codes = [
        code for code in codes
        if not any(dominates(ub, code) for ub in codes if ub is not code)
    ]
    filtered_codes.sort(key=priority, reverse=True)

    # Construct a JOIN term.
    result = filtered_codes[0]
    for code in filtered_codes[1:]:
        result = JOIN(code, result)
    return result


def dominates(lhs, rhs):
    """Strict domination relation."""
    lhs_rhs = try_decide_less(lhs, rhs)
    rhs_lhs = try_decide_less(rhs, lhs)
    return rhs_lhs is True and (lhs_rhs is False or lhs < rhs)


@memoize_args
def try_decide_less(lhs, rhs):
    """Weak decision oracle for Scott ordering among codes.

            | TOP   IVAR   NVAR   APP-ABS
    --------+---------------------------
        TOP | True  False  None   approx
       IVAR | True  delta  False  approx
       NVAR | True  False  ...    approx
    APP-ABS | True  approx approx approx

    Theorem: (soundness)
      - If try_decide_less(lhs, rhs) = True, then lhs [= rhs.
      - If try_decide_less(lhs, rhs) = False, then lhs [!= rhs.
    Theorem: (linear completeness)
      - If lhs [= rhs and both are linear,
        then try_decide_less(lhs, rhs) = True.
      - If lhs [!= rhs and both are linear,
        then try_decide_less(lhs, rhs) = False.
    Desired Theorem: (strong linear completeness)
      - If lhs [= u [= v [= rhs for some linear u, v,
        then try_decide_less(lhs, rhs) = True.
      - If rhs [= u [!= v [= lhs for some linear u, v,
        then try_decide_less(lhs, rhs) = False.

    Args:
        lhs, rhs : code
    Returns:
        True, False, or None

    """
    assert is_code(lhs), lhs
    assert is_code(rhs), rhs

    # Try simple cases.
    if lhs is BOT or lhs is rhs or rhs is TOP:
        return True
    if lhs is TOP and rhs is BOT:
        return False

    # Destructure lhs.
    TODO()

    # Destructure rhs.
    TODO()

    # Try incompatible cases.
    TODO()
    # if lhs is TOP and is_ivar(rhs_head):
    #     return False
    # if is_ivar(lhs_head) and rhs is BOT:
    #     return False

    # Eta expand until binder counts agree.
    # for _ in xrange(rhs_bound - lhs_bound):
    #     lhs_head = code_increment_ivars(lhs_head, 0)
    #     lhs_stack = stack_increment_ivars(lhs_stack, 0)
    # for _ in xrange(lhs_bound - rhs_bound):
    #     rhs_head = code_increment_ivars(rhs_head, 0)
    #     rhs_stack = stack_increment_ivars(rhs_stack, 0)

    # # Check for unknowns.
    # if is_nvar(lhs_head) or is_nvar(rhs_head):
    #     if lhs_head is rhs_head:
    #         return stack_try_decide_less(lhs_stack, rhs_stack)
    #     return None

    # # Try comparing stacks.
    # assert is_ivar(lhs_head) or lhs_head in INERT_ATOMS, lhs_head
    # assert is_ivar(rhs_head) or rhs_head in INERT_ATOMS, rhs_head
    # if is_ivar(lhs_head) and is_ivar(rhs_head):
    #     if lhs_head is not rhs_head:
    #         return False
    #     return stack_try_decide_less(lhs_stack, rhs_stack)

    # # Try approximating S.
    # assert lhs_head is S or rhs_head is S
    # if lhs_head is S and rhs_head is S:
    #     # Try to compare assuming lhs and rhs align.
    #     if stack_try_decide_less(lhs_stack, rhs_stack) is True:
    #         return True
    # if lhs_head is S:
    #     # Try to approximate lhs.
    #     for lhs_ub in iter_head_upper_bounds(lhs):
    #         if cont_try_decide_less(lhs_ub, rhs) is True:
    #             return True
    #     for lhs_lb in iter_head_lower_bounds(lhs):
    #         if cont_try_decide_less(lhs_lb, rhs) is False:
    #             return False
    # if rhs_head is S:
    #     # Try to approximate rhs.
    #     for rhs_lb in iter_head_lower_bounds(rhs):
    #         if cont_try_decide_less(lhs, rhs_lb) is True:
    #             return True
    #     for rhs_ub in iter_head_upper_bounds(rhs):
    #         if cont_try_decide_less(lhs, rhs_ub) is False:
    #             return False

    # Give up.
    return None


# ----------------------------------------------------------------------------
# Computation

def priority(code):
    return is_normal(code), complexity(code), code


@memoize_arg
def is_normal(code):
    if is_ivar(code) or is_nvar(code):
        return True
    elif is_abs(code):
        return is_normal(code[1])
    elif is_app(code):
        if is_abs(code[1]):
            return False
        return is_normal(code[1]) and is_normal(code[2])
    elif is_join(code):
        return is_normal(code[1]) and is_normal(code[2])
    elif is_quote(code):
        return is_normal(code[1])
    else:
        raise ValueError(code)


@memoize_arg
def try_compute_step(code):
    if not is_normal(code):
        return None
    if is_app(code):
        fun = code[1]
        arg = code[2]
        if is_abs(fun):
            body = fun[1]
            assert is_app(body), code
            lhs = body[1]
            rhs = body[2]
            return app(substitute(lhs, arg, 0), substitute(rhs, arg, 0))
        else:
            result = try_compute_step(fun)
            if result is not None:
                return app(result, arg)
            result = try_compute_step(arg)
            if result is not None:
                return app(fun, result)
            raise RuntimeError(code)
    elif is_join(code):
        lhs = code[1]
        rhs = code[2]
        result = try_compute_step(lhs)
        if result is not None:
            return join(result, rhs)
        result = try_compute_step(rhs)
        if result is not None:
            return join(lhs, result)
        raise RuntimeError(code)
    elif is_abs(code):
        result = try_compute_step(code[1])
        if result is not None:
            return ABS(result)
        raise RuntimeError(code)
    elif is_quote(code):
        result = try_compute_step(code[1])
        if result is not None:
            return QUOTE(result)
        raise RuntimeError(code)
    else:
        raise ValueError(code)
