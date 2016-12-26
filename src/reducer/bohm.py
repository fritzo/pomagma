"""Eager linear reduction of linear Bohm trees.

This library works with de-Bruijn-indexed linear-normal lambda terms.

All operations eagerly linearly reduce so that the only codes built are linear
Bohm trees. This contrasts older implementations by entirely avoiding use of
combinators and binding of nominal variables. The original motivation for
avoiding combinators was to make it easier to implement try_decide_less, which
is a core operation in normalizing JOIN terms.

CHANGELOG
2016-12-04 Initial prototype.
2016-12-11 Use linearizing approximations in order decision procedures.
2016-12-18 Add rules for quoting and reflected order.
2016-12-25 Add rules for nominal and quoted abstraction.
"""

from pomagma.compiler.util import memoize_arg, memoize_args, unique
from pomagma.reducer.syntax import (ABS, APP, BOOL, BOT, CODE, EQUAL, EVAL,
                                    IVAR, JOIN, LESS, MAYBE, QAPP, QQUOTE,
                                    QUOTE, TOP, UNIT, complexity, free_vars,
                                    is_abs, is_app, is_atom, is_code, is_ivar,
                                    is_join, is_nvar, is_quote, polish_parse,
                                    quoted_vars, sexpr_parse)
from pomagma.reducer.util import UnreachableError, trool_all, trool_any

I = ABS(IVAR(0))
K = ABS(ABS(IVAR(1)))
B = ABS(ABS(ABS(APP(IVAR(2), APP(IVAR(1), IVAR(0))))))
C = ABS(ABS(ABS(APP(APP(IVAR(2), IVAR(0)), IVAR(1)))))
S = ABS(ABS(ABS(APP(APP(IVAR(2), IVAR(0)), APP(IVAR(1), IVAR(0))))))

KI = ABS(ABS(IVAR(0)))
CB = ABS(ABS(ABS(APP(IVAR(1), APP(IVAR(2), IVAR(0))))))
CI = ABS(ABS(APP(IVAR(0), IVAR(1))))

true = K
false = KI


# ----------------------------------------------------------------------------
# Functional programming

@memoize_args
def _increment_rank(code, min_rank):
    if is_atom(code):
        return code
    elif is_nvar(code):
        return code
    elif is_ivar(code):
        rank = code[1]
        return IVAR(rank + 1) if rank >= min_rank else code
    elif is_abs(code):
        return ABS(_increment_rank(code[1], min_rank + 1))
    elif is_app(code):
        lhs = _increment_rank(code[1], min_rank)
        rhs = _increment_rank(code[2], min_rank)
        return APP(lhs, rhs)
    elif is_join(code):
        lhs = _increment_rank(code[1], min_rank)
        rhs = _increment_rank(code[2], min_rank)
        return JOIN(lhs, rhs)
    elif is_quote(code):
        return QUOTE(_increment_rank(code[1], min_rank))
    else:
        raise ValueError(code)
    raise UnreachableError((code, min_rank))


def increment_rank(code):
    """Increment rank of all free IVARs in code."""
    return _increment_rank(code, 0)


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
        return QUOTE(_try_decrement_rank(code[1], min_rank))
    else:
        raise ValueError(code)
    raise UnreachableError((code, min_rank))


def decrement_rank(code):
    """Decrement rank of all IVARs or err if IVAR(0) is free in code."""
    try:
        return _try_decrement_rank(code, 0)
    except CannotDecrementRank:
        raise ValueError(code)


EMPTY_SET = unique(frozenset())


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
        return unique(frozenset([rank])), EMPTY_SET
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
            unique(frozenset(r - 1 for r in body[0] if r)),
            unique(frozenset(r - 1 for r in body[1])),
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
    """Return whether code never copies a bound IVAR."""
    assert is_code(code), code
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
def substitute(code, value, rank, budget):
    """Substitute value for IVAR(rank) in code, decremeting higher IVARs.

    This is linear-eager, and will be lazy about nonlinear
    substitutions.

    """
    assert budget in (True, False), budget
    if is_atom(code):
        return code
    elif is_nvar(code):
        return code
    elif is_ivar(code):
        if code[1] == rank:
            return value
        elif code[1] > rank:
            return IVAR(code[1] - 1)
        else:
            return code
    elif is_app(code):
        lhs = code[1]
        rhs = code[2]
        linear = (is_cheap_to_copy(value) or
                  IVAR(rank) not in free_vars(lhs) or
                  IVAR(rank) not in free_vars(rhs))
        if linear or budget:
            # Eager substitution.
            if not linear:
                budget = False
            lhs = substitute(lhs, value, rank, False)
            rhs = substitute(rhs, value, rank, False)
            return app(lhs, rhs)
        else:
            # Lazy substitution.
            return APP(ABS(code), value)
    elif is_abs(code):
        body = substitute(code[1], increment_rank(value), rank + 1, budget)
        return abstract(body)
    elif is_join(code):
        lhs = substitute(code[1], value, rank, budget)
        rhs = substitute(code[2], value, rank, budget)
        return join(lhs, rhs)
    elif is_quote(code):
        body = substitute(code[1], value, rank, budget)
        return QUOTE(body)
    else:
        raise ValueError(code)
    raise UnreachableError((code, value, rank, budget))


TRY_CAST = {}


def casts(closure):

    def decorator(fun):
        TRY_CAST[closure] = fun
        return fun

    return decorator


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
    elif fun in TRY_CAST:
        casted = TRY_CAST[fun](arg)
        if casted is None:
            return APP(fun, arg)
        else:
            return casted
    else:
        raise ValueError(fun)
    raise UnreachableError((fun, arg))


@memoize_args
def abstract(code):
    """Abstract one de Bruijn variable and simplify."""
    if IVAR(0) in quoted_vars(code):
        raise ValueError(
            'Cannot abstract quoted variable from {}'.format(code))
    if code is TOP or code is BOT:
        return code
    elif is_app(code):
        fun = code[1]
        arg = code[2]
        if arg is IVAR(0) and IVAR(0) not in free_vars(fun):
            # Eta contract.
            return decrement_rank(fun)
        return ABS(code)
    elif is_join(code):
        lhs = abstract(code[1])
        rhs = abstract(code[2])
        return join(lhs, rhs)
    else:
        return ABS(code)
    raise UnreachableError(code)


@memoize_args
def qabstract(code):
    """Abstract one quoted de Bruijn variable and simplify."""
    if IVAR(0) not in quoted_vars(code):
        return app(app(B, abstract(code)), EVAL)
    elif is_abs(code):
        body = code[1]
        return app(C, abstract(qabstract(body)))
    elif is_app(code):
        fun = code[1]
        arg = code[2]
        return app(app(S, qabstract(fun)), qabstract(arg))
    elif is_join(code):
        lhs = qabstract(code[1])
        rhs = qabstract(code[2])
        return join(lhs, rhs)
    elif is_quote(code):
        body = code[1]
        if body is IVAR(0):
            return CODE
        else:
            return app(QAPP, QUOTE(abstract(body)))
    else:
        raise ValueError(code)
    raise UnreachableError(code)


@memoize_args
def anonymize(code, var, rank):
    """Convert a nominal variable to a de Bruijn variable."""
    if code is var:
        return IVAR(rank)
    elif is_atom(code) or is_nvar(code):
        return code
    elif is_ivar(code):
        return code if code[1] < rank else IVAR(code[1] + 1)
    elif is_abs(code):
        body = anonymize(code[1], var, rank + 1)
        return abstract(body)
    elif is_app(code):
        lhs = anonymize(code[1], var, rank)
        rhs = anonymize(code[2], var, rank)
        return app(lhs, rhs)
    elif is_join(code):
        lhs = anonymize(code[1], var, rank)
        rhs = anonymize(code[2], var, rank)
        return join(lhs, rhs)
    elif is_quote(code):
        body = anonymize(code[1], var, rank)
        return QUOTE(body)
    else:
        raise ValueError(code)


@memoize_args
def nominal_abstract(var, body):
    """Abstract a nominal variable and simplify."""
    anonymized = anonymize(body, var, 0)
    return abstract(anonymized)


@memoize_args
def nominal_qabstract(var, body):
    """Abstract a quoted nominal variable and simplify."""
    anonymized = anonymize(body, var, 0)
    return qabstract(anonymized)


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
    codes = set()
    for term in iter_join(lhs):
        codes.add(term)
    for term in iter_join(rhs):
        codes.add(term)
    return join_set(codes)


def join_set(codes):
    if not codes:
        return BOT
    if TOP in codes:
        return TOP
    if len(codes) == 1:
        return next(iter(codes))

    # Filter out strictly dominated codes (requires transitivity).
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
    """Weak strict domination relation: lhs =] rhs and lhs [!= rhs.

    This relation is used to reduce reduncancy in join(-, -) terms.
    This relation is required to be transitive, so that it extends from pairs
    to arbitrary finite sets of terms and so that it can induces a
    well-defined filtering operation in join(-, -).

    Theorem: (soundness) dominates(-,-) is weaker than the strict Scott
      ordering, ie if dominates(u, v) then u =] v and u [!= v.
    Corollary: dominates(-, -) is irreflexive and antisymmetric.
    Pf: Irreflexivity follows from strictness.
      Antisymmetry follows from antisymmetry of the Scott ordering. []
    Desired Theorem: dominates(-, -) is transitive.

    """
    lhs_rhs = try_decide_less(lhs, rhs)
    rhs_lhs = try_decide_less(rhs, lhs)
    return rhs_lhs is True and lhs_rhs is False


@memoize_args
def try_decide_less(lhs, rhs):
    """Weak decision procedure returning True, False, or None."""
    # Try a weak procedure.
    result = try_decide_less_weak(lhs, rhs)
    if result is not None:
        return result

    # Try to prove NLESS lhs rhs by approximation.
    for below_lhs in approximate(lhs, BOT):
        for above_rhs in approximate(rhs, TOP):
            if try_decide_less_weak(below_lhs, above_rhs) is False:
                return False

    # Try to prove LESS lhs rhs by approximation.
    for above_lhs in approximate(lhs, TOP):
        for below_rhs in approximate(rhs, BOT):
            if try_decide_less_weak(above_lhs, below_rhs) is True:
                return True

    # Give up.
    return None


@memoize_args
def approximate_var(code, direction, rank):
    """Locally approximate wrt one variable."""
    assert is_code(code), code
    assert direction is TOP or direction is BOT, direction
    assert isinstance(rank, int) and rank >= 0, rank
    result = set()
    if IVAR(rank) not in free_vars(code):
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
    elif is_quote(code):
        result.add(code)
    else:
        raise ValueError(code)
    return tuple(sorted(result, key=complexity))


def is_var(code):
    return is_nvar(code) or is_ivar(code)


@memoize_args
def approximate(code, direction):
    result = set()
    if is_atom(code) or is_var(code) or is_quote(code):
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
        for body in approximate(code[1], direction):
            result.add(abstract(body))
    elif is_join(code):
        for lhs in approximate(code[1], direction):
            for rhs in approximate(code[2], direction):
                result.add(join(lhs, rhs))
    else:
        raise ValueError(code)
    return tuple(sorted(result, key=complexity))


def unabstract(code):
    if is_abs(code):
        return code[1]
    else:
        return app(increment_rank(code), IVAR(0))


def unapply(code):
    args = []
    while is_app(code):
        args.append(code[2])
        code = code[1]
    return code, args


@memoize_args
def try_decide_less_weak(lhs, rhs):
    """Weak decision procedure returning True, False, or None."""
    assert is_code(lhs), lhs
    assert is_code(rhs), rhs

    # Try simple cases.
    if lhs is BOT or lhs is rhs or rhs is TOP:
        return True
    if lhs is TOP and rhs is BOT:
        return False

    # Destructure JOIN.
    if is_join(lhs):
        return trool_all(try_decide_less_weak(i, rhs) for i in iter_join(lhs))
    if is_join(rhs):
        # This requires we give up at unreduced terms.
        return trool_any(try_decide_less_weak(lhs, i) for i in iter_join(rhs))

    # Destructure ABS.
    while is_abs(lhs) or is_abs(rhs):
        lhs = unabstract(lhs)
        rhs = unabstract(rhs)
    assert lhs is not rhs, lhs

    # Destructure APP.
    lhs_head, lhs_args = unapply(lhs)
    rhs_head, rhs_args = unapply(rhs)

    # Try pointwise comparison.
    if lhs_args and len(lhs_args) == len(rhs_args):
        if try_decide_less_weak(lhs_head, rhs_head) is True:
            if all(try_decide_less_weak(i, j) is True
                   for i, j in zip(lhs_args, rhs_args)):
                return True

    # Give up at unreduced terms.
    if is_abs(lhs_head) or is_abs(rhs_head):
        return None
    if lhs_args and not is_var(lhs_head):
        return None
    if rhs_args and not is_var(rhs_head):
        return None

    # Distinguish solvable terms.
    if is_var(lhs_head) and is_var(rhs_head):
        if lhs_head is not rhs_head or len(lhs_args) != len(rhs_args):
            return False
        return trool_all(
            try_decide_less_weak(i, j)
            for i, j in zip(lhs_args, rhs_args)
        )

    # Distinguish quoted terms.
    if is_quote(lhs_head) and is_quote(rhs_head):
        return try_decide_equal(lhs_head[1], rhs_head[1])

    # Anything else is incomparable.
    return False


def try_decide_equal(lhs, rhs):
    return trool_all([try_decide_less(lhs, rhs), try_decide_less(rhs, lhs)])


# ----------------------------------------------------------------------------
# Type casting (eventually to be replaced by definable types)

@memoize_args
def _ground(code, direction, nvars, rank):
    if is_atom(code):
        return code
    elif is_nvar(code):
        return direction if code in nvars else code
    elif is_ivar(code):
        return direction if code[1] >= rank else code
    elif is_abs(code):
        body = _ground(code[1], direction, nvars, rank + 1)
        return abstract(body)
    elif is_app(code):
        lhs = _ground(code[1], direction, nvars, rank)
        rhs = _ground(code[2], direction, nvars, rank)
        return app(lhs, rhs)
    elif is_join(code):
        lhs = _ground(code[1], direction, nvars, rank)
        rhs = _ground(code[2], direction, nvars, rank)
        return join(lhs, rhs)
    elif is_quote(code):
        for var in free_vars(code):
            if is_nvar(var) and var in nvars:
                return direction
            if is_ivar(var) and var[1] >= rank:
                return direction
        return code
    else:
        raise ValueError(code)


def ground(code):
    """Approximate by grounding all free variables with [BOT, TOP]."""
    assert is_code(code)
    nvars = unique(frozenset(v for v in free_vars(code) if is_nvar(v)))
    return _ground(code, BOT, nvars, 0), _ground(code, TOP, nvars, 0)


@casts(UNIT)
def try_cast_unit(x):
    """Weak oracle closing x to type UNIT.

    Args:
        x : code in linear normal form
    Returns:
        TOP, BOT, I, or None

    """
    assert x is not None
    if x in (TOP, BOT, I):
        return x
    lb, ub = ground(x)
    if try_decide_less(lb, I) is False:
        return TOP
    if try_decide_less(ub, I) is True and try_decide_less(lb, BOT) is False:
        return I
    return None


@casts(BOOL)
def try_cast_bool(x):
    """Weak oracle closing x to type BOOL.

    Args:
        x : code in linear normal form
    Returns:
        TOP, BOT, K, APP(K, I), or None

    """
    assert x is not None
    if x in (TOP, BOT, K, KI):
        return x
    lb, ub = ground(x)
    if try_decide_less(lb, K) is False and try_decide_less(lb, KI) is False:
        return TOP
    if try_decide_less(lb, BOT) is False:
        if try_decide_less(ub, K) is True:
            return K
        if try_decide_less(ub, KI) is True:
            return KI
    return None


none = ABS(ABS(IVAR(1)))
some_TOP = ABS(ABS(APP(IVAR(0), TOP)))


@casts(MAYBE)
def try_cast_maybe(x):
    """Weak oracle closing x to type MAYBE.

    Args:
        x : code in linear normal form
    Returns:
        TOP, BOT, K, APP(K, APP(APP(C, I), ...)), or None

    """
    assert x is not None
    if x in (TOP, BOT, K):
        return x
    if is_app(x) and x[1] is K and is_app(x[2]) and x[2][1] is CI:
        return x
    lb, ub = ground(x)
    if try_decide_less(lb, none) is False:
        if try_decide_less(lb, some_TOP) is False:
            return TOP
    if try_decide_less(lb, BOT) is False:
        if try_decide_less(ub, none) is True:
            return none
        if try_decide_less(ub, some_TOP) is True:
            value = app(app(x, TOP), I)  # Is this safe?
            value = increment_rank(value)
            value = increment_rank(value)
            return ABS(ABS(APP(IVAR(0), value)))
    return None


@casts(CODE)
def try_cast_code(x):
    """Weak oracle closing x to type CODE.

    Args:
        x : code in linear normal form
    Returns:
        TOP, BOT, QUOTE(...), APP(QQUOTE, ...), APP(APP(QAPP, ...), ...),
        or None

    """
    assert x is not None
    if x is TOP or x is BOT or is_quote(x):
        return x
    if is_app(x):
        if x[1] is QQUOTE:
            return x
        if is_app(x[1]) and x[1][1] is QAPP:
            return x
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
    return _compute_step(code)


def _compute_step(code):
    assert not is_normal(code)
    if is_app(code):
        fun = code[1]
        arg = code[2]
        if is_abs(fun):
            assert not is_linear(fun), fun
            assert not is_linear(arg), arg
            body = fun[1]
            return substitute(body, arg, 0, True)
        if is_normal(fun):
            arg = _compute_step(arg)
        else:
            fun = _compute_step(fun)
        return app(fun, arg)
    elif is_join(code):
        lhs = _compute_step(code[1])  # Relies on prioritized sorting.
        rhs = code[2]
        return join(lhs, rhs)
    elif is_abs(code):
        body = _compute_step(code[1])
        return abstract(body)
    elif is_quote(code):
        body = _compute_step(code[1])
        return QUOTE(body)
    else:
        raise ValueError(code)
    raise UnreachableError(code)


SIGNATURE = {
    # Eager linear reduction.
    'APP': app,
    'ABS': abstract,
    'QABS': qabstract,
    'JOIN': join,
    # Conversion from nominal lambda calculus.
    'FUN': nominal_abstract,
    'QFUN': nominal_qabstract,
    # Conversion from combinatory algebra.
    'I': I,
    'K': K,
    'B': B,
    'C': C,
    'S': S,
}


@memoize_arg
def simplify(code):
    """Simplify code, converting to a linear Bohm tree."""
    assert is_code(code), code
    if is_atom(code):
        return SIGNATURE.get(code, code)
    elif is_ivar(code) or is_nvar(code):
        return code
    else:
        return SIGNATURE[code[0]](*map(simplify, code[1:]))


def reduce(code, budget=100):
    """Beta-reduce code up to budget."""
    code = simplify(code)
    for _ in xrange(budget):
        reduced = try_compute_step(code)
        if reduced is None:
            return code
        code = reduced
    return code


# ----------------------------------------------------------------------------
# Eager parsing

def sexpr_simplify(string):
    return sexpr_parse(string, SIGNATURE)


def polish_simplify(string):
    return polish_parse(string, SIGNATURE)


def _print_tiny(code, tokens):
    if code is TOP:
        tokens.append('T')
    elif code is BOT:
        tokens.append('_')
    elif is_ivar(code):
        rank = code[1]
        assert rank <= 9
        tokens.append(str(rank))
    elif is_abs(code):
        tokens.append('^')
        _print_tiny(code[1], tokens)
    elif is_app(code):
        head, args = unapply(code)
        tokens.append('(')
        _print_tiny(head, tokens)
        for arg in reversed(args):
            _print_tiny(arg, tokens)
        tokens.append(')')
    elif is_join(code):
        tokens.append('[')
        terms = list(iter_join(code))
        _print_tiny(terms[0], tokens)
        for term in terms[1:]:
            tokens.append('|')
            _print_tiny(term, tokens)
        tokens.append(']')
    else:
        raise NotImplementedError(code)


def print_tiny(code):
    """Compact printer for pure bohm trees."""
    tokens = []
    _print_tiny(code, tokens)
    return ''.join(tokens)
