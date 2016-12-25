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
"""

from pomagma.compiler.util import memoize_arg, memoize_args
from pomagma.reducer.syntax import (ABS, APP, BOT, EQUAL, EVAL, IVAR, JOIN,
                                    LESS, QAPP, QQUOTE, QUOTE, TOP, complexity,
                                    is_abs, is_app, is_atom, is_code, is_ivar,
                                    is_join, is_nvar, is_quote, polish_parse,
                                    sexpr_parse)
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
def increment_rank(code, min_rank):
    """Increment rank of all IVARs in code."""
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
    """Decrement rank of all IVARs or err if IVAR(0) is free in code."""
    try:
        return _try_decrement_rank(code, 0)
    except CannotDecrementRank:
        raise ValueError(code)


def is_const(code, rank=0):
    """Return true if IVAR(rank) is not free in code."""
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
            lhs = substitute(lhs, value, rank, False)
            rhs = substitute(rhs, value, rank, False)
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
    """Abstract one de Bruijn variable and simplify."""
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
    elif is_abs(body):
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


@memoize_args
def anonymize(code, var, rank):
    """Convert a nominal variable to a de Bruijn variable."""
    if code is var:
        return IVAR(rank)
    elif is_atom(code) or is_nvar(code) or is_quote(code):
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
    else:
        raise ValueError(code)


@memoize_args
def nominal_abstract(var, body):
    """Abstract a nominal variable and simplify."""
    anonymized = anonymize(body, var, 0)
    return abstract(anonymized)


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
        return app(increment_rank(code, 0), IVAR(0))


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

    # Give up at unreduced terms.
    if is_abs(lhs_head) or is_abs(rhs_head):
        if len(lhs_args) == len(rhs_args):
            if try_decide_less_weak(lhs_head, rhs_head) is True:
                if all(try_decide_less_weak(i, j) is True
                       for i, j in zip(lhs_args, rhs_args)):
                    return True
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


def reduce(code, budget=100):
    """Beta-reduce code up to budget."""
    for _ in xrange(budget):
        reduced = try_compute_step(code)
        if reduced is None:
            return code
        code = reduced
    return code


# ----------------------------------------------------------------------------
# Eager parsing

SIGNATURE = {
    'APP': app,
    'ABS': abstract,
    'JOIN': join,
    # Conversion from nominal lambda calculus.
    'FUN': nominal_abstract,
    # Conversion from combinatory algebra.
    'I': I,
    'K': K,
    'B': B,
    'C': C,
    'S': S,
}


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
