"""Nondeterministic Bohm trees with de Bruijn indexing.

This data structure intends to make it easy to implement the weak decision
procedure try_decide_less(-,-).

(Q1) Is reduction correct?
  Is cycle detection correct?
  Is domination filtering correct?
(Q2) Where should magic be inserted?
  In cont_try_decide_less(-,-)?
  In make_cont_set(-)?
(Q3) Is this reduction strategy compatible with quotients?
  How can it be extended with Todd-Coxeter forward-chaining?

"""

from collections import namedtuple
from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
from pomagma.reducer.code import APP, IVAR, TOP, BOT, I, K, B, C, S, J
from pomagma.reducer.code import complexity
from pomagma.reducer.code import is_app, is_nvar, is_ivar, is_atom
from pomagma.reducer.continuation import join_codes
from pomagma.reducer.util import LOG
from pomagma.reducer.util import pretty
from pomagma.util import TODO
import itertools

__all__ = ['reduce', 'simplify', 'try_decide_less']

SUPPORTED_TESTDATA = ['sk', 'join', 'lib']


def is_code(code):
    return isinstance(code, (tuple, str))


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


def list_to_stack(args):
    assert isinstance(args, list), args
    stack = None
    for arg in reversed(args):
        stack = arg, stack
    return stack


def iter_shared_list(shared_list):
    while shared_list is not None:
        arg, shared_list = shared_list
        yield arg


# ----------------------------------------------------------------------------
# Abstraction

@memoize_arg
def max_free_ivar(code):
    assert is_code(code), code
    if is_atom(code) or is_nvar(code):
        return -1
    elif is_ivar(code):
        return code[1]
    elif is_app(code):
        return max(max_free_ivar(code[1]), max_free_ivar(code[2]))
    else:
        raise NotImplementedError(code)


@memoize_args
def try_abstract(body):
    """IKBCSJ-eta abstraction algorithm for de Bruijn variables.

    Returns:
        (True, abstracted result) if var occurs in body, or
        (False, unabstracted ivar-incremented result) otherwise.

    """
    if is_atom(body) or is_nvar(body):
        return False, body  # Rule K
    elif is_ivar(body):
        rank = body[1]
        if rank == 0:
            return True, I  # Rule I
        else:
            return False, IVAR(rank - 1)  # Rule K-IVAR
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
        raise NotImplementedError(body)


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


@memoize_args
def code_increment_ivars(body, min_rank):
    if is_ivar(body):
        rank = body[1]
        if rank >= min_rank:
            rank += 1
        return IVAR(rank)
    elif is_atom(body) or is_nvar(body):
        return body
    elif is_app(body):
        lhs = code_increment_ivars(body[1], min_rank)
        rhs = code_increment_ivars(body[2], min_rank)
        return APP(lhs, rhs)
    else:
        raise NotImplementedError(body)


@memoize_args
def stack_increment_ivars(stack, min_rank):
    if stack is None:
        return None
    else:
        arg, stack = stack
        arg = cont_set_increment_ivars(arg, min_rank)
        stack = stack_increment_ivars(stack, min_rank)
        return arg, stack


# ----------------------------------------------------------------------------
# Continuations and sets of continuations

# Immutable shared cons-hashed continuations, in linear-beta-eta normal form.
Cont = namedtuple('Cont', ['type', 'args'])

# head : code
# stack : stack (frozenset continuation)
# bound : stack var
ContApp = namedtuple('ContApp', ['head', 'stack', 'bound'])

CONT_TYPE_TOP = intern('CONT_TOP')
CONT_TYPE_APP = intern('CONT_APP')
# TODO CONT_TYPE_JOIN = intern('CONT_JOIN')  # instead of cont_set
# TODO CONT_TYPE_QUOTE = intern('CONT_QUOTE')

INERT_ATOMS = frozenset([S])


def is_cont(arg):
    return isinstance(arg, Cont)


def is_cont_set(arg):
    return isinstance(arg, frozenset) and all(is_cont(c) for c in arg)


def is_stack(stack):
    while stack is not None:
        if not isinstance(stack, tuple) or len(stack) != 2:
            return False
        arg, stack = stack
        if not is_cont_set(arg):
            return False
    return True


@memoize_args
def make_cont(type_, args):
    """Continuations are linear-beta-eta normal forms."""
    if type_ is CONT_TYPE_APP:
        assert isinstance(args, ContApp), args
        head, stack, bound = args
        assert is_ivar(head) or is_nvar(head) or head in INERT_ATOMS, head
        if head is TOP:
            assert stack is None and bound == 0
        elif head is S:
            assert stack is not None
            assert stack[1] is not None
            assert stack[1][1] is not None
            assert not is_cheap_to_copy(stack[1][1][0])
        assert is_stack(stack), stack
        assert isinstance(bound, int) and bound >= 0, bound
    elif type_ is CONT_TYPE_TOP:
        assert args is None
    else:
        raise ValueError(type_)
    return Cont(type_, args)


def make_cont_app(head, stack, bound):
    assert is_code(head), head
    assert is_stack(stack), stack
    assert isinstance(bound, int) and bound >= 0, bound
    return make_cont(CONT_TYPE_APP, ContApp(head, stack, bound))


@memoize_arg
def make_cont_set(cont_set):
    assert is_cont_set(cont_set), cont_set

    # Filter out dominated continuations.
    cont_set = frozenset(
        cont
        for cont in cont_set
        if not any(cont_dominates(c, cont) for c in cont_set if c is not cont)
    )

    return cont_set


CONT_TOP = make_cont(CONT_TYPE_TOP, None)
CONT_SET_TOP = make_cont_set(frozenset([CONT_TOP]))

CONT_IVAR_0 = make_cont_app(IVAR(0), None, 0)
CONT_SET_IVAR_0 = make_cont_set(frozenset([CONT_IVAR_0]))


@memoize_args
def cont_increment_ivars(cont, min_rank):
    # FIXME is this right? Should we only increment vars below bound?
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        head, stack, bound = cont.args
        head = code_increment_ivars(head, min_rank + bound)
        stack = stack_increment_ivars(stack, min_rank + bound)
        return make_cont_app(head, stack, bound)
    elif cont.type is CONT_TYPE_TOP:
        return cont
    else:
        raise ValueError(cont)


@memoize_args
def cont_set_increment_ivars(cont_set, min_rank):
    assert is_cont_set(cont_set), cont_set
    return make_cont_set(frozenset(
        cont_increment_ivars(c, min_rank) for c in cont_set
    ))


# ----------------------------------------------------------------------------
# Conversion : code -> continuation

def is_cheap_to_copy(cont_set):
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
      Each TOP,BOT,I,K,B,C,J strictly reduces complexity. Moreover an S-redex
      gated by is_cheap_to_copy does not increase complexity. Hence any
      sequence of steps that do not increase complexity must eventually either
      terminate or cycle. Since cycles are detected, the computation must
      terminate. []

    """
    return cont_set_complexity(cont_set) <= complexity(S)


class PreContinuation(object):
    """Mutable temporary continuations, not in normal form."""

    __slots__ = 'head', 'stack', 'bound'

    def __init__(self, head, stack, bound):
        assert is_stack(stack), stack
        assert isinstance(bound, int) and bound >= 0
        self.head = head
        self.stack = stack
        self.bound = bound

    def seek_head(self):
        while is_app(self.head):
            arg = cont_set_from_codes((self.head[2],))
            self.stack = arg, self.stack
            self.head = self.head[1]
        return self.head

    def peek_at_arg(self, pos):
        assert isinstance(pos, int) and pos >= 0
        stack = self.stack
        for _ in xrange(pos):
            if stack is None:
                return CONT_SET_IVAR_0
            else:
                arg, stack = stack
        return arg

    def pop_args(self, count):
        assert isinstance(count, int) and count > 0
        args = []
        for _ in xrange(count):
            if self.stack is not None:
                arg, self.stack = self.stack
                args.append(arg)
            else:
                # eta expand
                self.head = code_increment_ivars(self.head, 0)
                self.stack = stack_increment_ivars(self.stack, 0)
                args = [cont_set_increment_ivars(arg, 0) for arg in args]
                args.append(CONT_SET_IVAR_0)
                self.bound += 1
        return args

    def push_arg(self, arg):
        assert is_cont_set(arg), arg
        self.stack = arg, self.stack

    def freeze(self):
        if self.head is TOP:
            return CONT_TOP
        else:
            return make_cont_app(self.head, self.stack, self.bound)


@memoize_args
def cont_set_from_codes(codes, stack=None, bound=0):
    assert all(map(is_code, codes)), codes
    pending = [PreContinuation(code, stack, bound) for code in codes]
    result = []
    while pending:
        precont = pending.pop()
        head = precont.seek_head()

        if is_ivar(head) or is_nvar(head):
            result.append(precont.freeze())
            continue
        elif head is TOP:
            return CONT_SET_TOP
        elif head is BOT:
            continue
        elif head is I:
            x, = precont.pop_args(1)
            head_cont_set = x
        elif head is K:
            x, y = precont.pop_args(2)
            head_cont_set = x
        elif head is B:
            x, y, z = precont.pop_args(3)
            yz = cont_set_app(y, z)
            precont.push_arg(yz)
            head_cont_set = x
        elif head is C:
            x, y, z = precont.pop_args(3)
            precont.push_arg(y)
            precont.push_arg(z)
            head_cont_set = x
        elif head is S:
            z = precont.peek_at_arg(3)
            if not is_cheap_to_copy(z):
                # TODO simplify S x y, to see if it is linear.
                result.append(precont.freeze())
                continue
            x, y, z = precont.pop_args(3)
            yz = cont_set_app(y, z)
            precont.push_arg(yz)
            precont.push_arg(z)
            head_cont_set = x
        elif head is J:
            x, y = precont.pop_args(2)
            head_cont_set = x | y
        else:
            raise NotImplementedError(head)

        stack = precont.stack
        bound = precont.bound
        for cont in head_cont_set:
            head = cont_to_code(cont)
            pending.append(PreContinuation(head, stack, bound))

    return make_cont_set(frozenset(result))


def cont_set_app(funs, args):
    assert is_cont_set(funs), funs
    assert is_cont_set(args), args
    codes = tuple(sorted(map(cont_to_code, funs)))
    stack = args, None
    return cont_set_from_codes(codes, stack)


# ----------------------------------------------------------------------------
# Conversion : continuation -> code

@memoize_arg
def cont_to_code(cont):
    """Returns code in linear normal form."""
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        head, stack, bound = cont.args
        while stack is not None:
            arg_cont_set, stack = stack
            arg_code = cont_set_to_code(arg_cont_set)
            head = APP(head, arg_code)
        for _ in xrange(bound):
            head = abstract(head)
        return head
    elif cont.type is CONT_TYPE_TOP:
        return TOP
    else:
        raise ValueError(cont)


@memoize_arg
def cont_set_to_code(cont_set):
    """Returns code in linear normal form.

    Desired Theorem: For any cont_set,
      cont_set_from_codes((cont_set_to_code(cont_set),)) == cont_set

    """
    assert is_cont_set(cont_set), cont_set
    codes = set(map(cont_to_code, cont_set))
    return join_codes(codes)


# ----------------------------------------------------------------------------
# Decision procedures

def try_decide_less(lhs, rhs):
    """Sound incomplete decision procedure for Scott ordering between codes.

    Args: lhs, rhs must be codes.
    Returns: True, False, or None.

    """
    lhs_term = cont_set_from_codes((lhs,))
    rhs_term = cont_set_from_codes((rhs,))
    return cont_set_try_decide_less(lhs_term, rhs_term)


@memoize_args
def cont_set_try_decide_less(lhs, rhs):
    assert is_cont_set(lhs), lhs
    assert is_cont_set(rhs), rhs
    return trool_all(
        trool_any(
            cont_try_decide_less(lhs_cont, rhs_cont)
            for rhs_cont in rhs
        )
        for lhs_cont in lhs
    )


@memoize_args
def cont_try_decide_less(lhs, rhs):
    """Weak decision oracle for Scott ordering.

         | TOP   IVAR   NVAR   S
    -----+---------------------------
     TOP | True  False  False  approx
    IVAR | True  delta  False  approx
    NVAR | True  False  delta  approx
       S | True  approx approx approx

    Theorem: (soundness)
      - If cont_try_decide_less(lhs, rhs) = True, then lhs [= rhs.
      - If cont_try_decide_less(lhs, rhs) = False, then lhs [!= rhs.
    Theorem: (linear completeness)
      - If lhs [= rhs and both are linear,
        then cont_try_decide_less(lhs, rhs) = True.
      - If lhs [!= rhs and both are linear,
        then cont_try_decide_less(lhs, rhs) = False.
    Desired Theorem: (strong linear completeness)
      - If lhs [= u [= v [= rhs for some linear u, v,
        then cont_try_decide_less(lhs, rhs) = True.
      - If rhs [= u [!= v [= lhs for some linear u, v,
        then cont_try_decide_less(lhs, rhs) = False.

    """
    assert is_cont(lhs), lhs
    assert is_cont(rhs), rhs

    # Try simple cases.
    if rhs is CONT_TOP or lhs is rhs:
        return True

    # Destructure lhs.
    if lhs.type is CONT_TYPE_APP:
        lhs_head, lhs_stack, lhs_bound = lhs.args
    elif lhs.type is CONT_TYPE_TOP:
        lhs_head, lhs_stack, lhs_bound = TOP, None, 0
    else:
        raise ValueError(lhs)

    # Destructure rhs.
    if rhs.type is CONT_TYPE_APP:
        rhs_head, rhs_stack, rhs_bound = rhs.args
    else:
        raise ValueError(lhs)

    # Try incompatible cases.
    if lhs_head is TOP:
        if is_ivar(rhs_head) or is_nvar(rhs_head):
            return False
    if is_ivar(lhs_head) and is_nvar(rhs_head):
        return False
    if is_nvar(lhs_head) and is_ivar(rhs_head):
        return False

    # Eta expand until binder counts agree.
    for _ in xrange(rhs_bound - lhs_bound):
        lhs_head = code_increment_ivars(lhs_head, 0)
        lhs_stack = stack_increment_ivars(lhs_stack, 0)
    for _ in xrange(lhs_bound - rhs_bound):
        rhs_head = code_increment_ivars(rhs_head, 0)
        rhs_stack = stack_increment_ivars(rhs_stack, 0)

    # Try comparing stacks.
    assert (is_ivar(lhs_head) or is_nvar(lhs_head) or
            lhs_head in INERT_ATOMS), lhs_head
    assert (is_ivar(rhs_head) or is_nvar(rhs_head) or
            rhs_head in INERT_ATOMS), rhs_head
    if is_ivar(lhs_head) and is_ivar(rhs_head):
        if lhs_head is not rhs_head:
            return False
        return stack_try_decide_less(lhs_stack, rhs_stack)
    if is_nvar(lhs_head) and is_nvar(rhs_head):
        if lhs_head is not rhs_head:
            return False
        return stack_try_decide_less(lhs_stack, rhs_stack)

    # Try approximating S.
    assert lhs_head is S or rhs_head is S
    if lhs_head is S and rhs_head is S:
        # Try to compare assuming lhs and rhs align.
        if stack_try_decide_less(lhs_stack, rhs_stack) is True:
            return True
    if lhs_head is S:
        # Try to approximate lhs.
        for lhs_ub in iter_head_upper_bounds(lhs):
            if cont_try_decide_less(lhs_ub, rhs) is True:
                return True
        for lhs_lb in iter_head_lower_bounds(lhs):
            if cont_try_decide_less(lhs_lb, rhs) is False:
                return False
    if rhs_head is S:
        # Try to approximate rhs.
        for rhs_lb in iter_head_lower_bounds(rhs):
            if cont_try_decide_less(lhs, rhs_lb) is True:
                return True
        for rhs_ub in iter_head_upper_bounds(rhs):
            if cont_try_decide_less(lhs, rhs_ub) is False:
                return False
    return None


def stack_try_decide_less(lhs_stack, rhs_stack):
    lhs_args = stack_to_list(lhs_stack)
    rhs_args = stack_to_list(rhs_stack)
    if len(lhs_args) != len(rhs_args):
        return False
    return trool_all(
        cont_set_try_decide_less(lhs_arg, rhs_arg)
        for lhs_arg, rhs_arg in itertools.izip(lhs_args, rhs_args)
    )


def cont_dominates(lhs, rhs):
    """Strict domination relation for continuations.

    Desired Theorem: if lhs dominates rhs, then all normal form continuations
      reachable from rhs are also reachable from lhs.

    """
    lhs_rhs = cont_try_decide_less(lhs, rhs)
    rhs_lhs = cont_try_decide_less(rhs, lhs)
    return lhs_rhs is True and rhs_lhs is False


# ----------------------------------------------------------------------------
# Linear approximation

S_LINEAR_UPPER_BOUNDS = (
    # S [= \x,y,z. x TOP(y z)
    APP(APP(B, B), APP(APP(C, I), TOP)),
    # S [=\x,y,z. x z(y TOP)
    APP(APP(C, APP(APP(B, B), C)), APP(APP(C, I), TOP)),
)

S_LINEAR_LOWER_BOUNDS = (
    # S =] \x,y,z. x BOT(y z)
    APP(APP(B, B), APP(APP(C, I), BOT)),
    # S =] \x,y,z. x z(y BOT)
    APP(APP(C, APP(APP(B, B), C)), APP(APP(C, I), BOT)),
)


def iter_head_upper_bounds(cont):
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        head, stack, bound = cont.args
        assert head is S, cont
        for head in S_LINEAR_UPPER_BOUNDS:
            for cont_ub in cont_set_from_codes((head,), stack, bound):
                yield cont_ub
    elif cont.type is CONT_TYPE_TOP:
        yield CONT_TOP
    else:
        raise ValueError(cont)


def iter_head_lower_bounds(cont):
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        head, stack, bound = cont.args
        assert head is S, cont
        for lb in cont_set_from_codes(S_LINEAR_LOWER_BOUNDS, stack, bound):
            yield lb
    elif cont.type is CONT_TYPE_TOP:
        yield CONT_TOP
    else:
        raise ValueError(cont)


def iter_lower_bounds(cont):
    TODO()


@memoize_arg
def close_under_lower_bounds(cont_set):
    assert is_cont_set(cont_set), cont_set
    pending = set(cont_set)
    result = set(cont_set)
    while pending:
        cont = pending.pop()
        for cont_lb in iter_lower_bounds(cont):
            if cont_lb not in result:
                pending.add(cont_lb)
                result.add(cont_lb)
    return result


# ----------------------------------------------------------------------------
# Reduction

@memoize_arg
def stack_try_compute_step(stack):
    if stack is None:
        return False, None
    cont_set, stack = stack
    progress, cont_set = cont_set_try_compute_step(cont_set)
    if progress:
        return True, cont_set
    progress, stack = stack_try_compute_step(stack)
    stack = cont_set, stack
    return progress, stack


@memoize_arg
def cont_try_compute_step(cont):
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        precont = PreContinuation(*cont.args)
        head = precont.seek_head()
        if head is S:
            x, y, z = precont.pop_args(3)
            assert not is_cheap_to_copy(z), z
            yz = cont_set_app(y, z)
            precont.push_arg(yz)
            precont.push_arg(z)
            codes = tuple(sorted(map(cont_to_code, x)))
            cont_set = cont_set_from_codes(codes, precont.stack, precont.bound)
            progress = True
        else:
            progress, precont.stack = stack_try_compute_step(precont.stack)
            if progress:
                cont = precont.freeze()
            cont_set = make_cont_set(frozenset([cont]))
        return progress, cont_set
    elif cont.type is CONT_TYPE_TOP:
        return False, CONT_SET_TOP
    else:
        raise ValueError(cont)


def cont_complexity(cont):
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        head, stack, bound = cont.args
        result = complexity(head)
        for arg in iter_shared_list(stack):
            result += cont_set_complexity(arg)
        result += bound
        return result
    elif cont.type is CONT_TYPE_TOP:
        return 1
    else:
        raise ValueError(cont)


def cont_set_complexity(cont_set):
    assert is_cont_set(cont_set), cont_set
    if not cont_set:
        return 1  # BOT
    return max(cont_complexity(cont) for cont in cont_set)


def priority(cont):
    return cont_complexity(cont), cont  # Deterministically break ties.


@memoize_arg
def cont_set_try_compute_step(cont_set):
    assert is_cont_set(cont_set), cont_set
    # TODO Separate cont_set into seen and pending.
    for cont in sorted(cont_set, key=priority):
        progress, new_cont_set = cont_try_compute_step(cont)
        if progress:
            new_cont_set = make_cont_set(cont_set | new_cont_set)
            if new_cont_set != cont_set:
                return True, new_cont_set
    return False, cont_set


def cont_is_normal(cont):
    assert is_cont(cont), cont
    progress, cont_set = cont_try_compute_step(cont)
    return not progress


@memoize_arg
def compute(code):
    assert is_code(code), code
    cont_set = cont_set_from_codes((code,))
    working = True
    while working:
        working, cont_set = cont_set_try_compute_step(cont_set)
    cont_set = make_cont_set(frozenset(
        c for c in cont_set if cont_is_normal(c)
    ))
    return cont_set_to_code(cont_set)


def reduce(code, budget=0):
    '''Beta-eta reduce code, ignoring budget.'''
    assert is_code(code), code
    assert isinstance(budget, int) and budget >= 0, budget
    LOG.info('reduce({})'.format(pretty(code)))
    code = compute(code)
    assert max_free_ivar(code) < 0, code
    return code


def simplify(code):
    '''Linearly beta-eta reduce.'''
    assert is_code(code), code
    LOG.info('simplify({})'.format(pretty(code)))
    cont_set = cont_set_from_codes((code,))
    code = cont_set_to_code(cont_set)
    assert max_free_ivar(code) < 0, code
    return code
