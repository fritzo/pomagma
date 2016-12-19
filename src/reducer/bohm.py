"""Eager linear reduction of linear Bohm trees.

This sketches a method of eagerly linearly reducing de Bruijn indexed codes so
that the only codes built are linear Bohm trees. This contrasts older
implementations by entirely avoiding use of combinators. The original
motivation for avoiding combinators was to make it easier to implement
try_decide_less in engines.continuation.

CHANGELOG
2016-12-04 Initial prototype.
2016-12-11 Use linearizing approximations in order decision procedures.
2016-12-18 Add rules for quoting and reflected order.
"""

from pomagma.compiler.util import memoize_arg, memoize_args
from pomagma.reducer.code import (
    TOP, BOT, IVAR, APP, ABS, JOIN, QUOTE, EVAL, QAPP, QQUOTE, LESS, EQUAL,
    is_code, is_atom, is_nvar, is_ivar, is_app, is_abs, is_join, is_quote,
    complexity,
)
from pomagma.reducer.util import UnreachableError

true = ABS(ABS(IVAR(1)))
false = ABS(ABS(IVAR(0)))


# ----------------------------------------------------------------------------
# Functional programming

@memoize_args
def increment_rank(code, min_rank):
    if is_atom(code):
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
    raise UnreachableError((code, min_rank))


class CannotDecrementRank(Exception):
    pass


@memoize_args
def _try_decrement_rank(code, min_rank):
    if is_atom(code):
        return code
    elif is_nvar(code):
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
    elif is_quote(code):
        return code
    else:
        raise ValueError(code)
    raise UnreachableError((code, min_rank))


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


EMPTY_SET = frozenset()


@memoize_arg
def _is_linear(code):
    """
    Returns:
        either None if code is nonlinear, else a pair (L, N) of frozensets,
        where L is the set of free IVARs appearing exactly once,
        and N is the set of free IVARs appearing multiply.
    """
    if is_atom(code):
        return EMPTY_SET, EMPTY_SET
    elif is_nvar(code):
        return EMPTY_SET, EMPTY_SET
    elif is_ivar(code):
        rank = code[1]
        return frozenset([rank]), EMPTY_SET
    elif is_app(code):
        lhs = _is_linear(code[1])
        rhs = _is_linear(code[2])
        if lhs is None or rhs is None:
            return None
        return lhs[0] | rhs[0], lhs[1] | rhs[1] | (lhs[0] & rhs[0])
    elif is_abs(code):
        body = _is_linear(code[1])
        if body is None or 0 in body[1]:
            return None
        return (
            frozenset(r - 1 for r in body[0] if r),
            frozenset(r - 1 for r in body[1]),
        )
    elif is_join(code):
        lhs = _is_linear(code[1])
        rhs = _is_linear(code[2])
        if lhs is None or rhs is None:
            return None
        return lhs[0] | rhs[0], lhs[1] | rhs[1]
    elif is_quote(code):
        return EMPTY_SET, EMPTY_SET
    else:
        raise ValueError(code)
    raise UnreachableError(code)


def is_linear(code):
    return _is_linear(code) is not None


def is_cheap_to_copy(code):
    """Guard to prevent nontermination.

    Theorem: If is_cheap_to_copy(-) is guards copies during beta steps,
    then the guarded reduction relation is terminating. Proof: Rank
    terms by the number ABS subterms that copy variables.   Linear
    reduction is terminating, and each nonlinear beta step strictly
    reduces rank. Hence there are finitely many linear reduction
    sequences.   []

    """
    return is_linear(code)


@memoize_args
def substitute(body, value, rank, budget):
    """Substitute value for IVAR(rank) in body, decremeting higher IVARs.

    This is linear-eager, and will be lazy about nonlinear
    substitutions.

    """
    assert budget in (True, False), budget
    if is_atom(body):
        return body
    elif is_nvar(body):
        return body
    elif is_ivar(body):
        if body[1] == rank:
            return value
        elif body[1] > rank:
            return IVAR(body[1] - 1)
        else:
            return body
    elif is_app(body):
        lhs = body[1]
        rhs = body[2]
        linear = (is_cheap_to_copy(value) or is_const(lhs, rank) or
                  is_const(rhs, rank))
        if linear or budget:
            # Eager substitution.
            if not linear:
                budget = False
            lhs = substitute(lhs, value, rank, budget)
            rhs = substitute(rhs, value, rank, budget)
            return app(lhs, rhs)
        else:
            # Lazy substitution.
            return APP(ABS(body), value)
    elif is_abs(body):
        body = substitute(body[1], increment_rank(value, 0), rank + 1, budget)
        return abstract(body)
    elif is_join(body):
        lhs = substitute(body[1], value, rank, budget)
        rhs = substitute(body[2], value, rank, budget)
        return join(lhs, rhs)
    elif is_quote(body):
        return body
    else:
        raise ValueError(body)
    raise UnreachableError((body, value, rank, budget))


@memoize_args
def app(fun, arg):
    """Apply function to argument and linearly reduce."""
    if fun is TOP:
        return fun
    elif fun is BOT:
        return fun
    elif is_nvar(fun):
        return APP(fun, arg)
    elif is_ivar(fun):
        return APP(fun, arg)
    elif is_app(fun):
        # Try to reduce strict binary functions of quoted codes.
        if fun[1] in (QAPP, LESS, EQUAL):
            lhs = fun[2]
            rhs = arg
            if lhs is TOP or rhs is TOP:
                return TOP
            elif lhs is BOT:
                if rhs is BOT or is_quote(rhs):
                    return BOT
            elif is_quote(lhs):
                if rhs is BOT:
                    return BOT
                elif is_quote(rhs):
                    if fun[1] is QAPP:
                        return QUOTE(app(lhs[1], rhs[1]))
                    if fun[1] is LESS:
                        ans = try_decide_less(lhs[1], rhs[1])
                    elif fun[1] is EQUAL:
                        ans = try_decide_equal(lhs[1], rhs[1])
                    else:
                        raise UnreachableError(fun[1])
                    if ans is True:
                        return true
                    elif ans is False:
                        return false
        return APP(fun, arg)
    elif is_abs(fun):
        body = fun[1]
        return substitute(body, arg, 0, False)
    elif is_join(fun):
        lhs = app(fun[1], arg)
        rhs = app(fun[2], arg)
        return join(lhs, rhs)
    elif is_quote(fun):
        return APP(fun, arg)
    elif fun is EVAL:
        if arg is TOP:
            return TOP
        elif arg is BOT:
            return BOT
        elif is_quote(arg):
            return arg[1]
        else:
            return APP(fun, arg)
    elif fun is QAPP:
        if arg is TOP:
            return TOP
        else:
            return APP(fun, arg)
    elif fun is QQUOTE:
        if arg is TOP:
            return TOP
        elif arg is BOT:
            return BOT
        elif is_quote(arg):
            return QUOTE(QUOTE(arg[1]))
        else:
            return APP(fun, arg)
    elif fun is LESS:
        if arg is TOP:
            return TOP
        else:
            return APP(fun, arg)
    elif fun is EQUAL:
        if arg is TOP:
            return TOP
        else:
            return APP(fun, arg)
    else:
        raise ValueError(fun)
    raise UnreachableError((fun, arg))


@memoize_args
def abstract(body):
    """Abstract one de Bruijn var and simplify."""
    if body is TOP:
        return body
    elif body is BOT:
        return body
    elif is_atom(body):
        return ABS(body)
    elif is_nvar(body):
        return ABS(body)
    elif is_ivar(body):
        return ABS(body)
    elif is_join(body):
        lhs = abstract(body[1])
        rhs = abstract(body[2])
        return join(lhs, rhs)
    elif is_app(body):
        if body[2] is IVAR(0) and is_const(body[1]):
            # Eta contract.
            return decrement_rank(body[1])
        else:
            return ABS(body)
    elif is_quote(body):
        return ABS(body)
    else:
        raise ValueError(body)
    raise UnreachableError(body)


# ----------------------------------------------------------------------------
# Scott ordering

def iter_join(code):
    """Destructs JOIN and BOT terms."""
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
    # TODO what to do about equivalence classes?
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
    """Strict domination relation: lhs =] rhs and lhs [!= rhs.

    TODO If lhs [=] rhs, allow lhs > rhs wrt arbitrary order, eg
    priority.

    """
    return try_prove_less(rhs, lhs) and try_prove_nless(lhs, rhs)


@memoize_args
def try_prove_less(lhs, rhs):
    """Weak proof procedure returning True or False."""
    return any(
        try_prove_less_linear(above_lhs, below_rhs)
        for above_lhs in approximate(lhs, TOP)
        for below_rhs in approximate(rhs, BOT)
    )


@memoize_args
def try_prove_nless(lhs, rhs):
    """Weak proof procedure returning True or False."""
    return any(
        try_prove_nless_linear(below_lhs, above_rhs)
        for below_lhs in approximate(lhs, BOT)
        for above_rhs in approximate(rhs, TOP)
    )


@memoize_args
def occurs(code, rank):
    if is_atom(code) or is_nvar(code) or is_quote(code):
        return False
    elif is_ivar(code):
        return code[1] == rank
    elif is_app(code):
        return occurs(code[1], rank) or occurs(code[2], rank)
    elif is_abs(code):
        return occurs(code[1], rank + 1)
    elif is_join(code):
        return occurs(code[1], rank) or occurs(code[2], rank)
    else:
        raise ValueError(code)
    raise UnreachableError((code, rank))


@memoize_args
def approximate_var(code, direction, rank):
    """Locally approximate wrt one variable."""
    assert is_code(code), code
    assert direction is TOP or direction is BOT, direction
    assert isinstance(rank, int) and rank >= 0, rank
    result = set()
    if not occurs(code, rank):
        result.add(code)
    elif is_ivar(code):
        assert code[1] == rank, code
        result.add(code)
        result.add(direction)
    elif is_app(code):
        for lhs in approximate_var(code[1], direction, rank):
            for rhs in approximate_var(code[2], direction, rank):
                result.add(app(lhs, rhs))
    elif is_abs(code):
        for body in approximate_var(code[1], direction, rank + 1):
            result.add(abstract(body))
    elif is_join(code):
        for lhs in approximate_var(code[1], direction, rank):
            for rhs in approximate_var(code[2], direction, rank):
                result.add(join(lhs, rhs))
    else:
        raise ValueError(code)
    return tuple(sorted(result, key=complexity))


@memoize_args
def approximate(code, direction):
    result = set()
    if is_atom(code) or is_ivar(code) or is_nvar(code):
        result.add(code)
    elif is_app(code):
        if is_abs(code[1]):
            for fun_body in approximate_var(code[1][1], direction, 0):
                for lhs in approximate(abstract(fun_body), direction):
                    for rhs in approximate(code[2], direction):
                        result.add(app(lhs, rhs))
        else:
            for lhs in approximate(code[1], direction):
                for rhs in approximate(code[2], direction):
                    result.add(app(lhs, rhs))
    elif is_abs(code):
        for body in approximate(code[1]):
            result.add(abstract(body))
    elif is_join(code):
        for lhs in approximate(code[1], direction):
            for rhs in approximate(code[2], direction):
                result.add(join(lhs, rhs))
    elif is_quote(code):
        # QUOTE flattens nonlearities, so only TOP or BOT can approximate.
        result.add(code)
        result.add(direction)
    else:
        raise ValueError(code)
    return tuple(sorted(result, key=complexity))


@memoize_args
def try_prove_less_linear(lhs, rhs):
    """Weak semidecision procedure to prove LESS lhs rhs."""
    assert is_code(lhs), lhs
    assert is_code(rhs), rhs

    # Try simple cases.
    if lhs is BOT or lhs is rhs or rhs is TOP:
        return True
    if lhs is TOP and rhs is BOT:
        return False

    # Decompose joins.
    if is_join(lhs):
        return all(try_prove_less_linear(i, rhs) for i in iter_join(lhs))
    if is_join(rhs):
        return any(try_prove_less_linear(lhs, i) for i in iter_join(rhs))

    # Distinguish variables.
    if is_ivar(lhs):
        if rhs is BOT:
            return False
        if is_ivar(rhs):
            return lhs is rhs
        if is_nvar(rhs):
            return False
    elif is_ivar(rhs):
        if lhs is TOP:
            return False
        if is_nvar(lhs):
            return False
    if is_nvar(lhs):
        if rhs is BOT:
            return False
        if is_nvar(rhs):
            return lhs is rhs
    elif is_nvar(rhs):
        if lhs is TOP:
            return False

    # TODO Try harder.

    # Give up.
    return False


@memoize_args
def try_prove_nless_linear(lhs, rhs):
    """Weak semidecision procedure to prove NLESS lhs rhs."""
    assert is_code(lhs), lhs
    assert is_code(rhs), rhs

    # Try simple cases.
    if lhs is BOT or lhs is rhs or rhs is TOP:
        return False
    if lhs is TOP and rhs is BOT:
        return True

    # Decompose joins.
    if is_join(lhs):
        return any(try_prove_nless_linear(i, rhs) for i in iter_join(lhs))
    if is_join(rhs):
        # TODO Try harder:
        # return all(try_prove_nless_linear(lhs, i) for i in iter_join(rhs))
        return False

    # Distinguish variables.
    if is_ivar(lhs):
        if rhs is BOT:
            return True
        if is_ivar(rhs):
            return lhs is not rhs
        if is_nvar(rhs):
            return False
    elif is_ivar(rhs):
        if lhs is TOP:
            return True
        if is_nvar(lhs):
            return True
    if is_nvar(lhs):
        if rhs is BOT:
            return True
        if is_nvar(rhs):
            return lhs is not rhs
    elif is_nvar(rhs):
        if lhs is TOP:
            return True

    # TODO Try harder.

    # Give up.
    return False


def try_decide_less(lhs, rhs):
    if try_prove_less(lhs, rhs):
        return True
    if try_prove_nless(lhs, rhs):
        return False
    return None


def try_decide_equal(lhs, rhs):
    if lhs is rhs:
        return True
    if try_prove_nless(lhs, rhs) or try_prove_nless(rhs, lhs):
        return False
    if try_prove_less(lhs, rhs) and try_prove_less(rhs, lhs):
        return True
    return None


# ----------------------------------------------------------------------------
# Computation

def priority(code):
    return is_normal(code), complexity(code), code


@memoize_arg
def is_normal(code):
    """Returns whether code is in linear normal form."""
    if is_atom(code) or is_nvar(code) or is_ivar(code):
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
    raise UnreachableError(code)


@memoize_arg
def try_compute_step(code):
    if is_normal(code):
        return None
    if is_app(code):
        fun = code[1]
        arg = code[2]
        if is_abs(fun):
            assert not is_linear(fun), fun
            assert not is_linear(arg), arg
            body = fun[1]
            return substitute(body, arg, 0, True)
        else:
            result = try_compute_step(fun)
            if result is not None:
                return app(result, arg)
            result = try_compute_step(arg)
            if result is not None:
                return app(fun, result)
            raise UnreachableError(code)
    elif is_join(code):
        lhs = code[1]
        rhs = code[2]
        result = try_compute_step(lhs)
        if result is not None:
            return join(result, rhs)
        result = try_compute_step(rhs)
        if result is not None:
            return join(lhs, result)
        raise UnreachableError(code)
    elif is_abs(code):
        result = try_compute_step(code[1])
        if result is not None:
            return abstract(result)
        raise UnreachableError(code)
    elif is_quote(code):
        result = try_compute_step(code[1])
        if result is not None:
            return QUOTE(result)
        raise UnreachableError(code)
    else:
        raise ValueError(code)
    raise UnreachableError(code)
