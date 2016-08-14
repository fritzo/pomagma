"""Nondeterministic Bohm trees with de Bruijn indexing.

This data structure intends to make it easy to implement the weak decision
procedure try_decide_less(-,-).

"""

from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
from pomagma.reducer.code import APP, TOP, BOT, I, K, B, C, S, J
from pomagma.reducer.code import is_app, is_atom
from pomagma.reducer.code import make_keyword, _term
from pomagma.util import TODO
import itertools

__all__ = ['try_decide_less']


def trool_all(args):
    result = True
    for arg in args:
        if arg is False:
            return False
        elif arg is None:
            result = None
    return result


def trool_any(args):
    result = False
    for arg in args:
        if arg is True:
            return True
        elif arg is None:
            result = None
    return result


def stack_to_list(stack):
    result = []
    while stack is not None:
        arg, stack = stack
        result.append(arg)
    return result


# ----------------------------------------------------------------------------
# Terms

_IVAR = make_keyword('IVAR')
_ABS = make_keyword('ABS')
_JOIN = make_keyword('JOIN')


def IVAR(rank):
    assert isinstance(rank, int) and rank >= 0, rank
    return _term(_IVAR, rank)


def ABS(term):
    return _term(_ABS, term)


def JOIN(args):
    assert isinstance(args, frozenset), args
    return _term(_JOIN, args)


def is_ivar(term):
    return isinstance(term, tuple) and term[0] is _IVAR


def is_abs(term):
    return isinstance(term, tuple) and term[0] is _ABS


def is_join(term):
    return isinstance(term, tuple) and term[0] is _JOIN


def is_point(term):
    return not is_join(term)


def is_normal(term):
    """Returns whether term is in linear-beta-eta normal form."""
    TODO()


def join_points(terms):
    """Joins a set of points into a single term, simplifying via heuristics."""
    assert all(not is_join(term) for term in terms)
    terms = set(terms)
    terms = frozenset(
        term
        for term in terms
        if term is not BOT and not any(
            try_decide_less_term(term, other)
            for other in terms if other is not term
        )
    )
    if not terms:
        return BOT
    elif len(terms) == 1:
        return next(iter(terms))
    else:
        return JOIN(terms)


def iter_points(term):
    if is_join(term):
        for subterm in iter_points(term[1]):
            yield subterm
    elif term is not BOT:
        yield term


# ----------------------------------------------------------------------------
# Abstraction

@memoize_arg
def max_free_var(term):
    if is_atom(term):
        return -1
    elif is_ivar(term):
        return term[1]
    elif is_app(term):
        return max(max_free_var(term[1]), max_free_var(term[2]))
    elif is_join(term):
        return max(max_free_var(arg) for arg in term[1])
    else:
        raise ValueError(term)


@memoize_args
def try_abstract(body):
    """IKBCSJ-eta abstraction algorithm for de Bruijn variables.

    Returns:
        (True, abstracted result) if var occurs in body, or
        (False, unabstracted result) if var does not occur in body.

    """
    if is_atom(body):
        return False, body  # Rule K
    elif is_ivar(body):
        rank = body[1]
        if rank == 0:
            return True, I  # Rule I
        else:
            return False, IVAR(rank - 1)  # Rule K
    elif is_app(body):
        if is_app(body[1]) and body[1][1] is J:
            lhs_found, lhs = try_abstract(body[1][2])
            rhs_found, rhs = try_abstract(body[2])
            if not lhs_found:
                if not rhs_found:
                    return False, APP(APP(J, lhs), rhs)  # Rule K
                elif rhs is I:
                    return True, APP(J, lhs)  # Rule J-eta
                else:
                    return True, APP(APP(B, APP(J, lhs)), rhs)  # Rule J-B
            else:
                if not rhs_found:
                    if lhs is I:
                        return True, APP(J, rhs)  # Rule J-eta
                    else:
                        return True, APP(APP(B, APP(J, rhs)), lhs)  # Rule J-B
                else:
                    return True, APP(APP(J, lhs), rhs)  # Rule J
        else:
            lhs_found, lhs = try_abstract(body[1])
            rhs_found, rhs = try_abstract(body[2])
            if not lhs_found:
                if not rhs_found:
                    return False, APP(lhs, rhs)  # Rule K
                elif rhs is I:
                    return True, lhs  # Rule eta
                else:
                    return True, APP(APP(B, lhs), rhs)  # Rule B
            else:
                if not rhs_found:
                    return True, APP(APP(C, lhs), rhs)  # Rule C
                else:
                    return True, APP(APP(S, lhs), rhs)  # Rule S
    else:
        raise ValueError(body)


def abstract(body):
    """TOP,BOT,I,K,B,C,S,J,eta-abstraction algorithm.

    Arg: a code with de Bruijn variables
    Returns: a code with de Bruijn variables

    """
    found, result = try_abstract(body)
    if found:
        return result
    elif result in (TOP, BOT):
        return result  # Rules TOP, BOT
    else:
        return APP(K, result)  # Rule K


@memoize_arg
def increment_ivars(body):
    if is_ivar(body):
        return IVAR(body[1] + 1)
    elif is_atom(body):
        return body
    elif is_app(body):
        return APP(increment_ivars(body[1]), increment_ivars(body[2]))
    elif is_join(body):
        return JOIN(frozenset(increment_ivars(arg) for arg in body[1]))
    else:
        raise ValueError(body)


# ----------------------------------------------------------------------------
# Conversion code -> term

def is_cheap_to_copy(term):
    return is_ivar(term) or term is TOP or term is BOT


def pop_arg(stack, bound_count):
    if stack is None:
        arg = IVAR(bound_count)
        bound_count += 1
        return arg, stack, bound_count
    else:
        arg, stack = stack
        return arg, stack, bound_count


@memoize_args
def code_to_term(code, stack=None, bound_count=0):
    """Linear-beta-eta normalize code into a Bohm tree."""
    pending = [(code, stack, bound_count)]
    continuations = []
    while pending:
        head, stack, bound_count = pending.pop()
        while is_app(head):
            arg = code_to_term(head[2])
            stack = arg, stack
            head = head[1]

        if is_ivar(head):
            continuations.append((head, stack, bound_count))
            continue
        elif head is TOP:
            return TOP
        elif head is BOT:
            continue
        elif head is I:
            x, stack, bound_count = pop_arg(stack, bound_count)
            points = iter_points(x)
        elif head is K:
            x, stack, bound_count = pop_arg(stack, bound_count)
            y, stack, bound_count = pop_arg(stack, bound_count)
            points = iter_points(x)
        elif head is B:
            x, stack, bound_count = pop_arg(stack, bound_count)
            y, stack, bound_count = pop_arg(stack, bound_count)
            z, stack, bound_count = pop_arg(stack, bound_count)
            yz = term_app(y, z)
            stack = yz, stack
            points = iter_points(x)
        elif head is C:
            x, stack, bound_count = pop_arg(stack, bound_count)
            y, stack, bound_count = pop_arg(stack, bound_count)
            z, stack, bound_count = pop_arg(stack, bound_count)
            stack = y, stack
            stack = z, stack
            points = iter_points(x)
        elif head is S:
            old_stack = stack
            old_bound_count = bound_count
            x, stack, bound_count = pop_arg(stack, bound_count)
            y, stack, bound_count = pop_arg(stack, bound_count)
            z, stack, bound_count = pop_arg(stack, bound_count)
            if is_cheap_to_copy(z):
                yz = term_app(y, z)
                stack = yz, stack
                stack = z, stack
                points = iter_points(x)
            else:
                continuations.append((S, old_stack, old_bound_count))
                continue
        elif head is J:
            x, stack, bound_count = pop_arg(stack, bound_count)
            y, stack, bound_count = pop_arg(stack, bound_count)
            points = itertools.chain(iter_points(x), iter_points(y))
        else:
            raise ValueError(head)

        for point in points:
            head = term_to_code(point)
            pending.append((head, stack, bound_count))

    TODO('FIXME this function should return a cont set')

    points = []
    for point, stack, bound_count in continuations:
        assert not is_abs(point), point
        while stack is not None:
            arg, stack = stack
            point = APP(point, arg)
        for _ in xrange(bound_count):
            point = ABS(point)
        points.append(point)

    return join_points(points)


def term_app(lhs, rhs):
    code = term_to_code(lhs)
    stack = rhs, None
    return code_to_term(code, stack)


# ----------------------------------------------------------------------------
# Conversion term -> code

@memoize_arg
def term_to_code(term):
    points = set(iter_points(term))
    if not points:
        return BOT
    codes = map(term_to_code_pointwise, points)
    # TODO Be smarter: return continuation.join_codes(codes)
    codes.sort(reverse=True)
    code = codes.pop()
    while codes:
        code = APP(J, code, codes.pop())
    return code


@memoize_arg
def term_to_code_pointwise(term):
    bound_count = 0
    while is_abs(term):
        bound_count += 1
        term = term[1]

    args = None
    while is_app(term):
        args = term[2], args
        term = term[1]

    assert is_ivar(term) or term in (TOP, BOT, S), term
    code = term

    while args is not None:
        arg_term, args = args
        arg_code = term_to_code(arg_term)
        code = APP(code, arg_code)

    for _ in xrange(bound_count):
        code = abstract(code)

    return code


# ----------------------------------------------------------------------------
# Decision procedures

def try_decide_less(lhs, rhs):
    """Sound incomplete decision procedure for Scott ordering between codes.

    Args: lhs, rhs must be codes.
    Returns: True, False, or None.

    """
    lhs_term = code_to_term(lhs)
    rhs_term = code_to_term(rhs)
    return try_decide_less_term(lhs_term, rhs_term)


@memoize_args
def try_decide_less_term(lhs, rhs):
    """Sound incomplete decision procedure for Scott ordering between terms.

    Args: lhs, rhs must be bohm trees.
    Returns: True, False, or None.

    """
    return trool_all(
        trool_any(
            try_decide_less_pointwise(lhs_point, rhs_point)
            for rhs_point in iter_points(rhs)
        )
        for lhs_point in iter_points(lhs)
    )


@memoize_args
def try_decide_less_pointwise(lhs, rhs):
    assert is_point(lhs), lhs
    assert is_point(rhs), rhs
    if lhs is BOT or lhs is rhs or rhs is TOP:
        return True
    lhs_cont = lhs, None, 0
    rhs_cont = rhs, None, 0
    return try_decide_less_cont(lhs_cont, rhs_cont)


def cont_pop_abs(cont):
    head, stack, bound_count = cont
    if is_abs(head):
        head = head[1]
    else:
        head = increment_ivars(head)  # FIXME is this right?
    return head, stack, bound_count


def cont_pop_app(cont):
    head, stack, bound_count = cont
    if is_app(head):
        stack = head[2], stack
        head = head[1]
    else:
        stack = IVAR(bound_count), stack
        bound_count += 1
    return head, stack, bound_count


@memoize_args
def try_decide_less_cont(lhs, rhs):
    assert isinstance(lhs, tuple) and len(lhs) == 3, lhs
    assert isinstance(rhs, tuple) and len(rhs) == 3, rhs
    if lhs[0] is BOT or rhs[0] is TOP or lhs is rhs:
        return True
    while is_abs(lhs[0]) or is_abs(rhs[0]):
        lhs = cont_pop_abs(lhs)
        rhs = cont_pop_abs(rhs)
    while is_app(lhs[0]):
        lhs = cont_pop_app(lhs)
    while is_app(rhs[0]):
        rhs = cont_pop_app(rhs)
    assert is_ivar(lhs[0]) or lhs[0] in (TOP, BOT, S), lhs[0]
    assert is_ivar(rhs[0]) or rhs[0] in (TOP, BOT, S), rhs[0]
    if lhs[2] != rhs[2]:
        TODO('deal with mismatches in bound_count')
    if is_ivar(lhs[0]) and is_ivar(rhs[0]):
        if lhs[0] is not rhs[0]:
            return False
        return try_decide_less_stack(lhs[1], rhs[1])
    assert lhs[0] is S or rhs[0] is S
    if lhs[0] is S and rhs[0] is S:
        # Try to compare assuming lhs and rhs align.
        if try_decide_less_stack(lhs[1], rhs[1]) is True:
            return True
    if lhs[0] is S:
        # Try to approximate lhs.
        for lhs_ub in iter_upper_bounds(lhs):
            if try_decide_less_cont(lhs_ub, rhs) is True:
                return True
        for lhs_lb in iter_lower_bounds(lhs):
            if try_decide_less_cont(lhs_lb, rhs) is False:
                return False
    if rhs[0] is S:
        # Try to approximate rhs.
        for rhs_lb in iter_lower_bounds(rhs):
            if try_decide_less_cont(lhs, rhs_lb) is True:
                return True
        for rhs_ub in iter_upper_bounds(rhs):
            if try_decide_less_cont(lhs, rhs_ub) is False:
                return False
    return None


def try_decide_less_stack(lhs_stack, rhs_stack):
    lhs_args = stack_to_list(lhs_stack)
    rhs_args = stack_to_list(rhs_stack)
    if len(lhs_args) != len(rhs_args):
        return False
    return trool_all(
        try_decide_less_term(lhs_arg, rhs_arg)
        for lhs_arg, rhs_arg in itertools.izip(lhs_args, rhs_args)
    )


# ----------------------------------------------------------------------------
# Linear approximations of S

S_LINEAR_UPPER_BOUNDS = [
    # S [= \x,y,z. x TOP(y z)
    APP(APP(B, B), APP(APP(C, I), TOP)),
    # S [=\x,y,z. x z(y TOP)
    APP(APP(C, APP(APP(B, B), C)), APP(APP(C, I), TOP))
]

S_LINEAR_LOWER_BOUNDS = [
    # S =] \x,y,z. (x BOT(y z) | x z(y BOT))
    APP(APP(J, APP(APP(B, B), APP(APP(C, I), BOT))),
        APP(APP(C, APP(APP(B, B), C)), APP(APP(C, I), BOT)))
]


def iter_upper_bounds(cont):
    head, stack, bound_count = cont
    assert head is S, head
    for head in S_LINEAR_UPPER_BOUNDS:
        yield code_to_term(head, stack, bound_count)


def iter_lower_bounds(cont):
    head, stack, bound_count = cont
    assert head is S, head
    for head in S_LINEAR_LOWER_BOUNDS:
        yield code_to_term(head, stack, bound_count)
