"""Nondeterministic linear Bohm trees with de Bruijn indexing.

This data structure intends to make it easy to implement the weak decision
procedure try_decide_less(-,-).

"""

from collections import namedtuple
from pomagma.compiler.util import memoize_args
from pomagma.reducer.code import IVAR, S, EVAL, LESS
from pomagma.reducer.code import complexity, is_nvar, is_ivar, is_code
from pomagma.reducer.util import iter_stack

# ----------------------------------------------------------------------------
# Continuations and sets of continuations

# Immutable shared cons-hashed continuations, in linear-beta-eta normal form.
Cont = namedtuple('Cont', ['type', 'args'])

# head : code
# stack : stack cont
# bound : int
ContApp = namedtuple('ContApp', ['head', 'stack', 'bound'])

CONT_TYPE_TOP = intern('CONT_TOP')
CONT_TYPE_BOT = intern('CONT_BOT')
CONT_TYPE_APP = intern('CONT_APP')
CONT_TYPE_JOIN = intern('CONT_JOIN')
CONT_TYPE_QUOTE = intern('CONT_QUOTE')
# CONT_TYPE_STACK = intern('CONT_STACK')  # TODO Focus on argument.

INERT_ATOMS = frozenset([S, EVAL, LESS])


def is_cont(arg):
    return isinstance(arg, Cont)


def is_stack(stack):
    while stack is not None:
        if not isinstance(stack, tuple) or len(stack) != 2:
            return False
        arg, stack = stack
        if not is_cont(arg):
            return False
    return True


@memoize_args
def _cont_make(type_, args):
    """Cons-hashed builder for Cont objects."""
    if type_ is CONT_TYPE_APP:
        assert isinstance(args, ContApp), args
        head, stack, bound = args
        assert is_ivar(head) or is_nvar(head) or head in INERT_ATOMS, head
        if head is S:
            assert stack is not None
            assert stack[1] is not None
            assert stack[1][1] is not None
            assert not is_cheap_to_copy(stack[1][1][0])
        elif head is EVAL:
            if stack is not None:
                assert stack[0] is not CONT_BOT
                assert stack[0] is not CONT_TOP
                assert stack[0].type is not CONT_TYPE_QUOTE
        elif head is LESS:
            if stack is not None:
                lhs = stack[0]
                assert lhs is not CONT_TOP
                if stack[1] is not None:
                    rhs = stack[1][0]
                    assert rhs is not CONT_TOP
                    assert not (lhs is CONT_BOT and rhs is CONT_BOT)
                    if lhs.type is CONT_TYPE_QUOTE:
                        assert rhs is not CONT_BOT
                        # TODO Be more strict:
                        # if rhs.type is CONT_TYPE_QUOTE:
                        #     assert cont_try_decide_less(lhs, rhs) is None
                    elif rhs.type is CONT_TYPE_QUOTE:
                        assert lhs is not CONT_TOP
        else:
            assert is_ivar(head) or is_nvar(head)
        assert is_stack(stack), stack
        assert isinstance(bound, int) and bound >= 0, bound
    elif type_ is CONT_TYPE_JOIN:
        assert isinstance(args, tuple) and len(args) == 2, args
        lhs, rhs = args
        assert is_cont(lhs), lhs
        assert is_cont(rhs), rhs
        assert lhs.type is not CONT_TYPE_JOIN, lhs
    elif type_ is CONT_TYPE_QUOTE:
        assert is_cont(args), args
    elif type_ is CONT_TYPE_TOP:
        assert args is None
    elif type_ is CONT_TYPE_BOT:
        assert args is None
    else:
        raise ValueError(type_)
    return Cont(type_, args)


def cont_hnf(head, stack, bound):
    assert is_code(head), head
    assert is_stack(stack), stack
    assert isinstance(bound, int) and bound >= 0, bound
    return _cont_make(CONT_TYPE_APP, ContApp(head, stack, bound))


def cont_join(lhs, rhs):
    assert is_cont(lhs), lhs
    assert is_cont(rhs), rhs
    parts = set(cont for arg in [lhs, rhs] for cont in cont_iter_join(arg))
    # Sort wrt priority, to reduce cons hashing thrashing.
    parts = sorted(parts, key=priority, reverse=True)
    result = parts[0]
    for part in parts[1:]:
        result = _cont_make(CONT_TYPE_JOIN, (part, result))
    return result


def cont_quote(body):
    assert is_cont(body), body
    return _cont_make(CONT_TYPE_QUOTE, body)


CONT_BOT = _cont_make(CONT_TYPE_BOT, None)
CONT_TOP = _cont_make(CONT_TYPE_TOP, None)
CONT_IVAR_0 = cont_hnf(IVAR(0), None, 0)
CONT_IVAR_1 = cont_hnf(IVAR(1), None, 0)
CONT_I = cont_hnf(IVAR(0), None, 1)
CONT_K = cont_hnf(IVAR(1), None, 2)
CONT_B = cont_hnf(
    IVAR(2),
    (cont_hnf(IVAR(1), (CONT_IVAR_0, None), 0), None),
    3,
)
CONT_C = cont_hnf(
    IVAR(2),
    (CONT_IVAR_0, (CONT_IVAR_1, None)),
    3,
)
CONT_S = cont_hnf(
    IVAR(2),
    (CONT_IVAR_0, (cont_hnf(IVAR(1), (CONT_IVAR_0, None), 0), None)),
    3,
)
CONT_TRUE = cont_hnf(IVAR(1), None, 2)
CONT_FALSE = cont_hnf(IVAR(0), None, 2)


def cont_iter_join(cont):
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_JOIN:
        for arg in cont.args:
            for part in cont_iter_join(arg):
                yield part
    elif cont.type is not CONT_TYPE_BOT:
        yield cont


def cont_complexity(cont):
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        head, stack, bound = cont.args
        result = complexity(head)
        for arg in iter_stack(stack):
            result = 1 + max(result, cont_complexity(arg))
        result += bound
        return result
    elif cont.type is CONT_TYPE_JOIN:
        return max(cont_complexity(part) for part in cont_iter_join(cont))
    elif cont.type is CONT_TYPE_QUOTE:
        body = cont.args
        result = 1 + cont_complexity(body)
        return result
    elif cont.type is CONT_TYPE_TOP:
        return 0
    elif cont.type is CONT_TYPE_BOT:
        return 0
    else:
        raise ValueError(cont)


def priority(cont):
    return cont_complexity(cont), cont  # Deterministically break ties.


def is_cheap_to_copy(cont):
    """Termination predicate.

    This predicate determines whether an S redex should yield to the next
    concurrent computation. To avoid thrashing, this wants to be as optimistic
    as possible, while still guaranteeing termination. This guarantees
    termination by ensuring that complexity will decrease during reduction.

    Theorem: The following is a fair (i.e. complete) scheduling strategy:
      - schedule any minimal-complexity task first;
      - yield whenever an S redex fails the is_cheap_to_copy predicate;
      - on resuming a task, immedately perform the S-step that yielded;
      - detect and terminate cycles.
    Proof: We need to show that every reduction sequence either terminates or
      yields. There are only finitely many states below any given complexity.
      Each TOP,BOT,I,K,B,C strictly reduces complexity. Moreover an S-redex
      gated by is_cheap_to_copy does not increase complexity. Hence any
      sequence of steps that do not increase complexity must eventually either
      terminate or cycle. Since cycles are detected, the computation must
      terminate. []

    """
    assert is_cont(cont), cont
    return cont_complexity(cont) <= complexity(S)
