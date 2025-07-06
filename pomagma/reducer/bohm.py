"""
Eager linear reduction of linear Böhm trees.

This library works with de-Bruijn-indexed linear-normal lambda terms.

All operations eagerly linearly reduce so that the only terms built are linear
Böhm trees. This contrasts older implementations by entirely avoiding use of
combinators and binding of nominal variables. The original motivation for
avoiding combinators was to make it easier to implement try_decide_less, which
is a core operation in normalizing JOIN terms.

CHANGELOG
2016-12-04 Initial prototype.
2016-12-11 Use linearizing approximations in order decision procedures.
2016-12-18 Add rules for quoting and reflected order.
2016-12-25 Add rules for nominal and quoted abstraction.
2016-12-27 Treat nominal and de Bruijn variables differently. TODO revert?
2016-12-31 Fix bug in substitute(-,-,-,-); tests pass.
2025-07-05 Distinguish between SEMI and UNIT.
"""

from collections.abc import Callable, Collection, Iterable, Iterator

from pomagma.compiler.util import memoize_arg, memoize_args, unique
from pomagma.reducer import syntax
from pomagma.reducer.syntax import (
    ABS,
    APP,
    BOOL,
    BOT,
    CODE,
    EVAL,
    IVAR,
    JOIN,
    MAYBE,
    NUM,
    QAPP,
    QEQUAL,
    QLESS,
    QQUOTE,
    QUOTE,
    SEMI,
    TOP,
    UNIT,
    Term,
    Y,
    anonymize,
    complexity,
    free_vars,
    is_abs,
    is_app,
    is_atom,
    is_ivar,
    is_join,
    is_nvar,
    is_quote,
    polish_parse,
    quoted_vars,
    sexpr_parse,
    sexpr_print,
)
from pomagma.reducer.util import UnreachableError, logged, trool_all, trool_any

SUPPORTED_TESTDATA = ["sk", "join", "quote", "types", "lib", "semi", "unit"]

# TODO Make strong version not horribly expensive.
TRY_DECIDE_LESS_STRONG = False

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

pretty = sexpr_print


def maybe_pretty(term):
    return "None" if term is None else pretty(term)


################################################################
# Functional programming


@memoize_args
def _increment_rank(term, min_rank):
    if is_atom(term):
        return term
    if is_nvar(term):
        return term
    if is_ivar(term):
        rank = term[1]
        return IVAR(rank + 1) if rank >= min_rank else term
    if is_abs(term):
        return ABS(_increment_rank(term[1], min_rank + 1))
    if is_app(term):
        lhs = _increment_rank(term[1], min_rank)
        rhs = _increment_rank(term[2], min_rank)
        return APP(lhs, rhs)
    if is_join(term):
        lhs = _increment_rank(term[1], min_rank)
        rhs = _increment_rank(term[2], min_rank)
        return JOIN(lhs, rhs)
    if is_quote(term):
        return QUOTE(_increment_rank(term[1], min_rank))
    raise ValueError(term)
    raise UnreachableError((term, min_rank))


def increment_rank(term):
    """Increment rank of all free IVARs in term."""
    return _increment_rank(term, 0)


class CannotDecrementRank(Exception):
    pass


@memoize_args
def _try_decrement_rank(term: Term, min_rank: int) -> Term:
    if is_atom(term):
        return term
    if is_nvar(term):
        return term
    if is_ivar(term):
        rank: int = term[1]  # type: ignore[assignment]
        if rank < min_rank:
            return term
        if rank == min_rank:
            raise CannotDecrementRank
        return IVAR(rank - 1)
    if is_app(term):
        lhs = _try_decrement_rank(term[1], min_rank)  # type: ignore[arg-type]
        rhs = _try_decrement_rank(term[2], min_rank)  # type: ignore[arg-type]
        return APP(lhs, rhs)
    if is_abs(term):
        return ABS(_try_decrement_rank(term[1], min_rank + 1))  # type: ignore[arg-type]
    if is_join(term):
        lhs = _try_decrement_rank(term[1], min_rank)  # type: ignore[arg-type]
        rhs = _try_decrement_rank(term[2], min_rank)  # type: ignore[arg-type]
        return JOIN(lhs, rhs)
    if is_quote(term):
        return QUOTE(_try_decrement_rank(term[1], min_rank))  # type: ignore[arg-type]
    raise ValueError(term)
    raise UnreachableError((term, min_rank))


def decrement_rank(term: Term) -> Term:
    """Decrement rank of all IVARs or err if IVAR(0) is free in term."""
    try:
        return _try_decrement_rank(term, 0)
    except CannotDecrementRank:
        raise ValueError(term)


EMPTY_SET = unique(frozenset())


@memoize_arg
def _is_linear(term):
    """
    Returns:
        either None if term is nonlinear, else a pair (L, N) of frozensets,
        where L is the set of free IVARs appearing at least once,
        and N is the set of free IVARs appearing at least twice.
    """
    if is_atom(term):
        if term is Y or term is EVAL:
            return None
        return EMPTY_SET, EMPTY_SET
    if is_nvar(term):
        return EMPTY_SET, EMPTY_SET
    if is_ivar(term):
        rank = term[1]
        return unique(frozenset([rank])), EMPTY_SET
    if is_app(term):
        lhs = _is_linear(term[1])
        rhs = _is_linear(term[2])
        if lhs is None or rhs is None:
            return None
        return lhs[0] | rhs[0], lhs[1] | rhs[1] | (lhs[0] & rhs[0])
    if is_abs(term):
        body = _is_linear(term[1])
        if body is None or 0 in body[1]:
            return None
        return (
            unique(frozenset(r - 1 for r in body[0] if r)),
            unique(frozenset(r - 1 for r in body[1])),
        )
    if is_join(term):
        lhs = _is_linear(term[1])
        rhs = _is_linear(term[2])
        if lhs is None or rhs is None:
            return None
        return lhs[0] | rhs[0], lhs[1] | rhs[1]
    if is_quote(term):
        return EMPTY_SET, EMPTY_SET
    raise ValueError(term)
    raise UnreachableError(term)


def is_linear(term):
    """Return whether term and its subterms never copy an input argument.

    This definition is tuned for use as a beta-redex guard to prevent
    nontermination, under the alias is_cheap_to_copy.

    Design decisions:
    * Nondeterminism is allowed, so that e.g. K|K(I) is linear.
    * TOP is linear.
    * Y is nonlinear.
    * QUOTE(x) is linear for any x, hence EVAL must be nonlinear.

    """
    assert isinstance(term, Term), term
    return _is_linear(term) is not None


def is_cheap_to_copy(term):
    """Guard to prevent nontermination.

    Theorem: If is_cheap_to_copy(-) is guards copies during beta steps,
      then the guarded reduction relation is terminating.
    Proof: Rank terms by the number ABS subterms that copy variables. Linear
      reduction (ie with no copying) is terminating, and each nonlinear beta
      step strictly reduces rank. Hence there are finitely many linear
      reduction sequences. []

    """
    return is_linear(term)


@memoize_args
def _permute_rank(term, min_rank, max_rank):
    assert min_rank < max_rank
    if is_atom(term) or is_nvar(term):
        return term
    if is_ivar(term):
        rank = term[1]
        if rank < min_rank or max_rank < rank:
            return term
        if rank == max_rank:
            return IVAR(min_rank)
        return IVAR(rank + 1)
    if is_abs(term):
        body = _permute_rank(term[1], min_rank + 1, max_rank + 1)
        return ABS(body)
    if is_app(term):
        lhs = _permute_rank(term[1], min_rank, max_rank)
        rhs = _permute_rank(term[2], min_rank, max_rank)
        return APP(lhs, rhs)
    if is_join(term):
        lhs = _permute_rank(term[1], min_rank, max_rank)
        rhs = _permute_rank(term[2], min_rank, max_rank)
        return JOIN(lhs, rhs)
    if is_quote(term):
        body = _permute_rank(term[1], min_rank, max_rank)
        return QUOTE(body)
    raise ValueError(term)
    raise UnreachableError((term, min_rank, max_rank))


def permute_rank(term: Term, rank: int) -> Term:
    """Permute IVARs from [0,1,2...,rank] to [1,2,...,rank,0]."""
    assert isinstance(term, Term), term
    assert isinstance(rank, int) and rank >= 0, rank
    return _permute_rank(term, 0, rank) if rank > 0 else term


# @logged(pretty, pretty, str, str, returns=pretty)
@memoize_args
def substitute(term: Term, value: Term, rank: int, budget: bool) -> Term:
    """
    Substitute value for IVAR(rank) in term, decrementing higher IVARs.

    This is linear-eager, and will be lazy about nonlinear
    substitutions.
    """
    assert budget in (True, False), budget
    if is_atom(term):
        return term
    if is_nvar(term):
        return term
    if is_ivar(term):
        i: int = term[1]  # type: ignore[assignment]
        if i == rank:
            return value
        if i > rank:  # type: ignore[operator]
            return IVAR(i - 1)
        return term
    if is_app(term):
        lhs = term[1]
        rhs = term[2]
        linear = (
            is_cheap_to_copy(value)
            or IVAR(rank) not in free_vars(lhs)
            or IVAR(rank) not in free_vars(rhs)
        )
        if linear or budget:
            # Eager substitution.
            if not linear:
                budget = False
            lhs = substitute(lhs, value, rank, False)  # type: ignore[arg-type]
            rhs = substitute(rhs, value, rank, False)  # type: ignore[arg-type]
            return app(lhs, rhs)
        # Lazy substitution.
        term = permute_rank(term, rank)
        return APP(ABS(term), value)
    if is_abs(term):
        body = substitute(term[1], increment_rank(value), rank + 1, budget)  # type: ignore[arg-type]
        return abstract(body)
    if is_join(term):
        lhs = substitute(term[1], value, rank, budget)  # type: ignore[arg-type]
        rhs = substitute(term[2], value, rank, budget)  # type: ignore[arg-type]
        return join(lhs, rhs)
    if is_quote(term):
        body = substitute(term[1], value, rank, budget)  # type: ignore[arg-type]
        return QUOTE(body)
    raise ValueError(term)
    raise UnreachableError((term, value, rank, budget))


TRY_CAST: dict[Term, Callable[[Term], Term]] = {}


def casts(closure):
    def decorator(fun):
        TRY_CAST[closure] = fun
        return fun

    return decorator


# @logged(pretty, pretty, returns=pretty)
@memoize_args
def app(fun: Term, arg: Term) -> Term:
    """Apply function to argument and linearly reduce."""
    if fun is TOP:
        return fun
    if fun is BOT:
        return fun
    if is_nvar(fun):
        return APP(fun, arg)
    if is_ivar(fun):
        return APP(fun, arg)
    if is_app(fun):
        # Try to reduce strict binary functions of quoted terms.
        if fun[1] in (QAPP, QLESS, QEQUAL):
            lhs = fun[2]
            rhs = arg
            if lhs is TOP or rhs is TOP:
                return TOP  # type: ignore[no-any-return]
            if lhs is BOT:
                if rhs is BOT or is_quote(rhs):
                    return BOT  # type: ignore[no-any-return]
            elif isinstance(lhs, Term) and is_quote(lhs):
                if rhs is BOT:
                    return BOT  # type: ignore[no-any-return]
                if is_quote(rhs):
                    if fun[1] is QAPP:
                        return QUOTE(app(lhs[1], rhs[1]))  # type: ignore[arg-type]
                    if fun[1] is QLESS:
                        ans = try_decide_less(lhs[1], rhs[1])  # type: ignore[arg-type]
                    elif fun[1] is QEQUAL:
                        ans = try_decide_equal(lhs[1], rhs[1])  # type: ignore[arg-type]
                    else:
                        raise UnreachableError(fun[1])
                    if ans is True:
                        return true
                    if ans is False:
                        return false
        return APP(fun, arg)
    if is_abs(fun):
        body: Term = fun[1]  # type: ignore[assignment]
        return substitute(body, arg, 0, False)
    if is_join(fun):
        lhs = app(fun[1], arg)  # type: ignore[arg-type]
        rhs = app(fun[2], arg)  # type: ignore[arg-type]
        return join(lhs, rhs)
    if is_quote(fun):
        return APP(fun, arg)
    if fun is Y:
        if arg is TOP:
            return TOP
        if arg is BOT:
            return BOT
        if arg is Y:
            return BOT
        return APP(Y, arg)
    if fun is EVAL:
        if arg is TOP:
            return TOP
        if arg is BOT:
            return BOT
        if is_quote(arg):
            return arg[1]  # type: ignore[no-any-return]
        return APP(fun, arg)
    if fun is QAPP:
        if arg is TOP:
            return TOP
        return APP(fun, arg)
    if fun is QQUOTE:
        if arg is TOP:
            return TOP
        if arg is BOT:
            return BOT
        if is_quote(arg):
            return QUOTE(QUOTE(arg[1]))  # type: ignore[no-any-return]
        return APP(fun, arg)
    if fun is QLESS:
        if arg is TOP:
            return TOP
        return APP(fun, arg)
    if fun is QEQUAL:
        if arg is TOP:
            return TOP
        return APP(fun, arg)
    if fun in TRY_CAST:
        while is_app(arg) and arg[1] is fun:
            arg = arg[2]  # type: ignore[assignment]
        casted = TRY_CAST[fun](arg)
        if casted is None:
            return APP(fun, arg)
        return casted
    raise ValueError(fun)
    raise UnreachableError((fun, arg))


# @logged(pretty, returns=pretty)
@memoize_args
def abstract(term: Term) -> Term:
    """Abstract one de Bruijn variable and simplify."""
    if IVAR(0) in quoted_vars(term):
        raise ValueError(f"Cannot abstract quoted variable from {term}")
    if term is TOP or term is BOT:
        return term
    if is_app(term):
        fun: Term = term[1]  # type: ignore[assignment]
        arg: Term = term[2]  # type: ignore[assignment]
        if arg is IVAR(0) and IVAR(0) not in free_vars(fun):
            # Eta contract.
            return decrement_rank(fun)
        return ABS(term)
    if is_join(term):
        lhs = abstract(term[1])  # type: ignore[arg-type]
        rhs = abstract(term[2])  # type: ignore[arg-type]
        return join(lhs, rhs)
    return ABS(term)
    raise UnreachableError(term)


# @logged(pretty, returns=pretty)
@memoize_args
def qabstract(term: Term) -> Term:
    """Abstract one quoted de Bruijn variable and simplify."""
    if IVAR(0) not in quoted_vars(term):
        return app(app(B, abstract(term)), EVAL)
    if is_abs(term):
        body: Term = term[1]  # type: ignore[assignment]
        return app(C, abstract(qabstract(body)))  # FIXME increment rank
    if is_app(term):
        fun: Term = term[1]  # type: ignore[assignment]
        arg: Term = term[2]  # type: ignore[assignment]
        return app(app(S, qabstract(fun)), qabstract(arg))
    if is_join(term):
        lhs = qabstract(term[1])  # type: ignore[arg-type]
        rhs = qabstract(term[2])  # type: ignore[arg-type]
        return join(lhs, rhs)
    if is_quote(term):
        body = term[1]  # type: ignore[assignment]
        if body is IVAR(0):
            return CODE
        return app(QAPP, QUOTE(abstract(body)))
    raise ValueError(term)
    raise UnreachableError(term)


# @logged(pretty, pretty, returns=pretty)
@memoize_args
def nominal_abstract(var: Term, body: Term) -> Term:
    """Abstract a nominal variable and simplify."""
    anonymized = anonymize(body, var, convert)
    return abstract(anonymized)


# @logged(pretty, pretty, returns=pretty)
@memoize_args
def nominal_qabstract(var: Term, body: Term) -> Term:
    """Abstract a quoted nominal variable and simplify."""
    anonymized = anonymize(body, var, convert)
    return qabstract(anonymized)


################################################################
# Scott ordering


def iter_join(term: Term) -> Iterator[Term]:
    """Destructs JOIN and BOT terms."""
    if is_join(term):
        lhs: Term = term[1]  # type: ignore[assignment]
        rhs: Term = term[2]  # type: ignore[assignment]
        for part in iter_join(lhs):
            yield part
        for part in iter_join(rhs):
            yield part
    elif term is not BOT:
        yield term


# @logged(pretty, pretty, returns=pretty)
@memoize_args
def join(lhs: Term, rhs: Term) -> Term:
    """Join two terms, modulo linear Scott ordering."""
    terms: set[Term] = set()
    for part in iter_join(lhs):
        terms.add(part)
    for part in iter_join(rhs):
        terms.add(part)
    return join_set(terms)


def join_set(terms: Collection[Term]) -> Term:
    if not terms:
        return BOT  # type: ignore[no-any-return]
    if TOP in terms:
        return TOP  # type: ignore[no-any-return]
    if len(terms) == 1:
        return next(iter(terms))

    # Filter out strictly dominated terms (requires transitivity).
    filtered_terms = [
        term
        for term in terms
        if not any(dominates(ub, term) for ub in terms if ub is not term)
    ]
    filtered_terms.sort(key=priority, reverse=True)

    # Construct a JOIN term.
    result = filtered_terms[0]
    for term in filtered_terms[1:]:
        result = JOIN(term, result)
    return result


def dominates(lhs: Term, rhs: Term) -> bool:
    """
    Weak strict domination relation: lhs =] rhs and lhs [!= rhs.

    This relation is used to reduce redundancy in join(-, -) terms.
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


# @logged(pretty, pretty, returns=str)
def try_decide_less(lhs: Term, rhs: Term) -> bool | None:
    if TRY_DECIDE_LESS_STRONG:
        return try_decide_less_strong(lhs, rhs)
    return try_decide_less_weak(lhs, rhs)


@memoize_args
def try_decide_less_strong(lhs: Term, rhs: Term) -> bool | None:
    """
    Weak decision procedure returning True, False, or None.

    The behavior on closed terms should approximate Scott ordering. The
    behavior on variables is defined with the particular application of
    deciding order among definitions in reducer.lib. We assume all IVARs are
    bound and all NVARS are free, so that for example:

        # Refrain from decision until x is defined.
        try_decide_less(NVAR('x'), BOT) = None

        # False for some grounding substitution.
        try_decide_less(IVAR(0), BOT) = False

    Thus a property of an IVAR is False iff it fails for all substitutions,
    whereas a property of an NVAR is False iff it fails for any substitution.
    A property is True iff it holds for all substitutions (for IVAR or NVAR);
    the difference is only between False vs None.

    Note that this differs from the convention in the rest of pomagma, where
    terms are implicitly universally quantified (NVARS act like IVARS).
    """
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
def approximate_var(term: Term, direction: Term, rank: int) -> Iterable[Term]:
    """Locally approximate wrt one variable."""
    assert isinstance(term, Term), term
    assert direction is TOP or direction is BOT, direction
    assert isinstance(rank, int) and rank >= 0, rank
    result = set()
    if IVAR(rank) not in free_vars(term):
        result.add(term)
    elif is_ivar(term):
        assert term[1] == rank, term
        result.add(term)
        result.add(direction)
    elif is_app(term):
        fun: Term = term[1]  # type: ignore[assignment]
        arg: Term = term[2]  # type: ignore[assignment]
        for fun_ in approximate_var(fun, direction, rank):
            for arg_ in approximate_var(arg, direction, rank):
                result.add(app(fun_, arg_))
    elif is_abs(term):
        body: Term = term[1]  # type: ignore[assignment]
        for body_ in approximate_var(body, direction, rank + 1):
            result.add(abstract(body_))
    elif is_join(term):
        lhs: Term = term[1]  # type: ignore[assignment]
        rhs: Term = term[2]  # type: ignore[assignment]
        for lhs_ in approximate_var(lhs, direction, rank):
            for rhs_ in approximate_var(rhs, direction, rank):
                result.add(join(lhs_, rhs_))
    elif is_quote(term):
        result.add(term)
    else:
        raise ValueError(term)
    return tuple(sorted(result, key=complexity))


@memoize_args
def approximate(term: Term, direction: Term) -> Iterable[Term]:
    result = set()
    if is_atom(term) or is_nvar(term) or is_ivar(term) or is_quote(term):
        result.add(term)
    elif is_app(term):
        fun: Term = term[1]  # type: ignore[assignment]
        arg: Term = term[2]  # type: ignore[assignment]
        if is_abs(fun):
            fun_body: Term = fun[1]  # type: ignore[assignment]
            for fun_body_ in approximate_var(fun_body, direction, 0):
                for lhs_ in approximate(abstract(fun_body_), direction):
                    for rhs_ in approximate(arg, direction):
                        result.add(app(lhs_, rhs_))
        else:
            lhs: Term = term[1]  # type: ignore[assignment]
            rhs: Term = term[2]  # type: ignore[assignment]
            for lhs_ in approximate(lhs, direction):
                for rhs_ in approximate(rhs, direction):
                    result.add(app(lhs_, rhs_))
    elif is_abs(term):
        body: Term = term[1]  # type: ignore[assignment]
        for body_ in approximate(body, direction):
            result.add(abstract(body_))
    elif is_join(term):
        lhs = term[1]  # type: ignore[assignment]
        rhs = term[2]  # type: ignore[assignment]
        for lhs_ in approximate(lhs, direction):
            for rhs_ in approximate(rhs, direction):
                result.add(join(lhs_, rhs_))
    else:
        raise ValueError(term)
    return tuple(sorted(result, key=complexity))


def unabstract(term: Term) -> Term:
    if is_abs(term):
        return term[1]  # type: ignore[no-any-return]
    return app(increment_rank(term), IVAR(0))


def unapply(term: Term) -> tuple[Term, list[Term]]:
    args = []
    while is_app(term):
        args.append(term[2])
        term = term[1]  # type: ignore[assignment]
    return term, args


@memoize_args
def try_decide_less_weak(lhs: Term, rhs: Term) -> bool | None:
    """Weak decision procedure returning True, False, or None."""
    assert isinstance(lhs, Term), lhs
    assert isinstance(rhs, Term), rhs

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
            if all(
                try_decide_less_weak(i, j) is True for i, j in zip(lhs_args, rhs_args)
            ):
                return True

    # Give up at unreduced terms.
    if is_nvar(lhs_head) or is_nvar(rhs_head):
        return None
    if is_abs(lhs_head) or is_abs(rhs_head):
        return None
    if lhs_args and not is_ivar(lhs_head):
        return None
    if rhs_args and not is_ivar(rhs_head):
        return None

    # Distinguish solvable terms.
    if is_ivar(lhs_head) and is_ivar(rhs_head):
        if lhs_head is not rhs_head or len(lhs_args) != len(rhs_args):
            return False
        return trool_all(try_decide_less_weak(i, j) for i, j in zip(lhs_args, rhs_args))

    # Distinguish quoted terms.
    if is_quote(lhs_head) and is_quote(rhs_head):
        return try_decide_equal(lhs_head[1], rhs_head[1])  # type: ignore[arg-type]

    # Anything else is incomparable.
    return False


def try_decide_equal(lhs: Term, rhs: Term) -> bool | None:
    return trool_all([try_decide_less(lhs, rhs), try_decide_less(rhs, lhs)])


################################################################
# Type casting (eventually to be replaced by definable types)


@memoize_args
def _ground(term, direction, nvars, rank):
    if is_atom(term):
        return term
    if is_nvar(term):
        return direction if term in nvars else term
    if is_ivar(term):
        return direction if term[1] >= rank else term
    if is_abs(term):
        body = _ground(term[1], direction, nvars, rank + 1)
        return abstract(body)
    if is_app(term):
        lhs = _ground(term[1], direction, nvars, rank)
        rhs = _ground(term[2], direction, nvars, rank)
        return app(lhs, rhs)
    if is_join(term):
        lhs = _ground(term[1], direction, nvars, rank)
        rhs = _ground(term[2], direction, nvars, rank)
        return join(lhs, rhs)
    if is_quote(term):
        for var in free_vars(term):
            if is_nvar(var) and var in nvars:
                return direction
            if is_ivar(var) and var[1] >= rank:
                return direction
        return term
    raise ValueError(term)
    raise UnreachableError(term)


def ground(term):
    """Approximate by grounding all free variables with [BOT, TOP]."""
    assert isinstance(term, Term)
    nvars = unique(frozenset(v for v in free_vars(term) if is_nvar(v)))
    return _ground(term, BOT, nvars, 0), _ground(term, TOP, nvars, 0)


@casts(SEMI)
def try_cast_semi(x):
    """
    Weak oracle closing x to type SEMI.

    Args:
        x : term in linear normal form
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


@casts(UNIT)
def try_cast_unit(x):
    """
    Weak oracle closing x to type UNIT.

    Args:
        x : term in linear normal form
    Returns:
        TOP, I, or None
    """
    assert x is not None
    if x in (TOP, I):
        return x
    lb, ub = ground(x)
    if try_decide_less(lb, I) is False:
        return TOP
    if try_decide_less(ub, I) is True:
        return I
    return None


@casts(BOOL)
def try_cast_bool(x):
    """
    Weak oracle closing x to type BOOL.

    Args:
        x : term in linear normal form
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
    """
    Weak oracle closing x to type MAYBE.

    Args:
        x : term in linear normal form
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


@casts(NUM)
def try_cast_num(x):
    """
    Weak oracle closing x to type NUM = Y MAYBE.

    Args:
        x : term in linear normal form
    Returns:
        TOP, BOT, zero, succ(BOT), succ(zero), ... or None

    TODO support infinity = Y(succ)
    """
    head = try_cast_maybe(x)  # type: ignore[arg-type]
    if head in (None, TOP, BOT, K):
        return head
    # head is succ(...) = some(...) = K(CI(...))
    # Extract the predecessor from K(CI(predecessor))
    pred_x = app(app(head, TOP), ABS(IVAR(0)))
    pred_value = try_cast_num(pred_x)
    if pred_value is None:
        return None
    if pred_value is TOP:
        return TOP
    pred_value = increment_rank(pred_value)
    pred_value = increment_rank(pred_value)
    return ABS(ABS(APP(IVAR(0), pred_value)))


@casts(CODE)
def try_cast_code(x):
    """
    Weak oracle closing x to type CODE.

    Args:
        x : term in linear normal form
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


################################################################
# Computation


def priority(term):
    return is_normal(term), complexity(term), term


@memoize_arg
def is_normal(term):
    """Returns whether term is in normal form, i.e. is irreducible."""
    if is_atom(term) or is_nvar(term) or is_ivar(term):
        return True
    if is_abs(term):
        return is_normal(term[1])
    if is_app(term):
        fun = term[1]
        arg = term[2]
        if not is_normal(fun) or not is_normal(arg):
            return False
        if is_abs(fun):
            return False
        if fun is Y and is_abs(arg):
            return False
        return True
    if is_join(term):
        return is_normal(term[1]) and is_normal(term[2])
    if is_quote(term):
        return True
    raise ValueError(term)
    raise UnreachableError(term)


@logged(pretty, returns=maybe_pretty)
@memoize_arg
def try_compute_step(term):
    if is_normal(term):
        return None
    return _compute_step(term)


def _compute_step(term):
    assert not is_normal(term)
    if is_app(term):
        fun = term[1]
        arg = term[2]
        if is_abs(fun):
            assert not is_linear(fun), fun
            assert not is_linear(arg), arg
            body = fun[1]
            return substitute(body, arg, 0, True)
        if fun is Y and is_abs(arg):
            body = arg[1]
            return substitute(body, term, 0, False)
        if is_normal(fun):
            return app(fun, _compute_step(arg))
        return app(_compute_step(fun), arg)
    if is_join(term):
        lhs = _compute_step(term[1])  # Relies on prioritized sorting.
        rhs = term[2]
        return join(lhs, rhs)
    if is_abs(term):
        body = _compute_step(term[1])
        return abstract(body)
    raise ValueError(term)
    raise UnreachableError(term)


SIGNATURE = {
    "QUOTE": QUOTE,
    # Eager linear reduction.
    "APP": app,
    "ABS": abstract,
    "JOIN": join,
    # Conversion from nominal lambda calculus.
    "FUN": nominal_abstract,
    # Conversion from combinatory algebra.
    "I": I,
    "K": K,
    "B": B,
    "C": C,
    "S": S,
}

convert = syntax.Transform(**SIGNATURE)


@logged(pretty, returns=pretty)
def simplify(term):
    """Simplify term, converting to a linear Bohm tree."""
    return convert(term)


@logged(pretty, returns=pretty)
def reduce(term, budget=100):
    """Beta-reduce term up to budget."""
    term = simplify(term)
    for _ in range(budget):
        reduced = try_compute_step(term)
        if reduced is None:
            return term
        term = reduced
    return term


################################################################
# Eager parsing


def sexpr_simplify(string):
    return sexpr_parse(string, convert)


def polish_simplify(string):
    return polish_parse(string, convert)


def _print_tiny(term, tokens):
    if term is TOP:
        tokens.append("T")
    elif term is BOT:
        tokens.append("_")
    elif is_ivar(term):
        rank = term[1]
        assert rank <= 9
        tokens.append(str(rank))
    elif is_abs(term):
        tokens.append("^")
        _print_tiny(term[1], tokens)
    elif is_app(term):
        head, args = unapply(term)
        tokens.append("(")
        _print_tiny(head, tokens)
        for arg in reversed(args):
            _print_tiny(arg, tokens)
        tokens.append(")")
    elif is_join(term):
        tokens.append("[")
        parts = list(iter_join(term))
        _print_tiny(parts[0], tokens)
        for part in parts[1:]:
            tokens.append("|")
            _print_tiny(part, tokens)
        tokens.append("]")
    else:
        raise NotImplementedError(term)


def print_tiny(term):
    """Compact printer for pure bohm trees."""
    tokens = []
    _print_tiny(term, tokens)
    return "".join(tokens)
