"""Nondeterministic Bohm trees with de Bruijn indexing.

This data structure intends to make it easy to implement the weak decision
procedure try_decide_less(-,-).

"""

from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
from pomagma.reducer.code import APP, TOP, BOT, I, K, B, C, S, J, is_app
from pomagma.reducer.code import make_keyword, _term
from pomagma.reducer.oracle import TROOL_AND, TROOL_OR
from pomagma.util import TODO

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


def is_normal(term):
    """Returns whether term is in linear-beta-eta normal form."""
    TODO()


# ----------------------------------------------------------------------------
# Conversions between bohm trees <--> codes

def make_join(terms):
    terms = set(terms)
    terms = frozenset(
        term
        for term in terms
        if term is not BOT and not any(
            try_decide_less(term, other)
            for other in terms if other is not term
        )
    )
    if not terms:
        return BOT
    elif len(terms) == 1:
        return next(iter(terms))
    else:
        return JOIN(terms)


def apply_stack(head, args):
    code = head
    while args is not None:
        arg, args = args
        code = APP(code, arg)
    return code


def code_to_bohm_tree(code):
    """Linear normalizes code into a Bohm tree."""
    terms = []
    pending = [code]
    while pending:
        head = pending.pop()
        args = None
        while is_app(head):
            args = head[2], args
            head = head[1]
        if head is I:
            TODO()
            continue
        elif head is K:
            TODO()
        elif head is B:
            TODO()
        elif head is C:
            TODO()
        elif head is S:
            TODO()
        elif head is J:
            TODO()
        else:
            raise ValueError(head)
        TODO('process args and abs and add to terms')
    return make_join(terms)


def bohm_tree_to_code(bt):
    if not bt:
        return BOT
    codes = map(term_to_code, bt)
    codes.sort(reverse=True)
    code = codes.pop()
    while codes:
        code = APP(J, code, codes.pop())
    return code


def term_to_code(term):
    bound_count = 0
    while is_abs(term):
        bound_count += 1
        term = term[1]

    args = None
    while is_app(term):
        args = term[2], args
        term = term[1]

    assert not is_abs(term, term)
    assert is_ivar(term) or term in (TOP, BOT, S), term
    code = term

    while args is not None:
        arg_bt, args = args
        arg_code = bohm_tree_to_code(arg_bt)
        code = APP(code, arg_code)

    for _ in xrange(term.bound_count):
        code = abstract(code)

    return code


@memoize_args
def try_abstract(body):
    """Returns (whether var was found, abstracted result)."""
    if is_ivar(body):
        rank = body[1]
        if rank == 0:
            return True, I
        else:
            return False, IVAR(rank - 1)
    elif is_app(body):
        lhs_found, lhs_result = try_abstract(body[1])
        rhs_found, rhs_result = try_abstract(body[2])
        if lhs_found:
            if rhs_found:
                return True, APP(APP(S, lhs_result), rhs_result)
            else:
                return True, APP(APP(C, lhs_result), rhs_result)
        else:
            if rhs_found:
                return True, APP(APP(B, lhs_result), rhs_result)
            else:
                return False, APP(lhs_result, rhs_result)
    else:
        raise ValueError(body)


def abstract(body):
    found, result = try_abstract(body)
    return result if found else APP(K, result)


# ----------------------------------------------------------------------------
# Decision procedures

def iter_terms(term):
    if is_join(term):
        for subterm in iter_terms(term[1]):
            yield subterm
    elif term is not BOT:
        yield term


@memoize_arg
def try_decide_less(lhs, rhs):
    """Sound incomplete decision procedure for Scott ordering between terms.

    Args:
        lhs, rhs must be bohm trees.
    Returns:
        True, False, or None.

    """
    result = True
    for lhs_point in iter_terms(lhs):
        lhs_result = False
        for rhs_point in iter_terms(rhs):
            lhs_rhs_result = pointwise_try_decide_less(lhs_point, rhs_point)
            lhs_result = TROOL_OR[lhs_result, lhs_rhs_result]
        result = TROOL_AND(result, lhs_result)
    return result


@memoize_args
def pointwise_try_decide_less(lhs, rhs):
    """Sound incomplete decision procedure for Scott ordering between points
    (terms that are not joins).

    Args:
        lhs, rhs must be terms.
    Returns:
        True, False, or None.

    """
    assert not is_join(lhs), lhs
    assert not is_join(rhs), rhs
    if lhs is BOT or lhs is rhs or rhs is TOP:
        return True
    TODO()
    return None
