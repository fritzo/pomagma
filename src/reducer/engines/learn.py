"""Reduction engine with reduction step learning."""

from collections import namedtuple
from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
from pomagma.reducer.code import APP, JOIN, IVAR, TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import complexity, is_nvar, is_ivar
from pomagma.reducer.code import is_code, is_atom, is_app, is_join
from pomagma.reducer.code import sexpr_print as print_code
from pomagma.reducer.util import LOG
from pomagma.reducer.util import logged
from pomagma.reducer.util import pretty
from pomagma.reducer.util import stack_to_list, iter_stack
from pomagma.reducer.util import trool_all, trool_any
import itertools

__all__ = ['reduce', 'simplify', 'try_decide_less']

SUPPORTED_TESTDATA = ['sk', 'join']


# ----------------------------------------------------------------------------
# Tracing

def print_stack(stack):
    return '[{}]'.format(
        ', '.join(print_cont(v) for v in iter_stack(stack)))


def print_cont(cont):
    type_, args = cont
    if type_ is CONT_TYPE_APP:
        return 'APP: {} {} {}'.format(
            print_code(args.head),
            print_stack(args.stack),
            args.bound,
        )
    elif type_ is CONT_TYPE_JOIN:
        lhs, rhs = cont.args
        lhs = print_cont(lhs)
        rhs = print_cont(rhs)
        return 'JOIN: {} {}'.format(lhs, rhs)
    elif type_ is CONT_TYPE_TOP:
        return 'TOP'
    else:
        raise ValueError(cont)


@memoize_arg
def print_set(print_item):

    def printer(items):
        return '{{{}}}'.format(', '.join(print_item(i) for i in items))

    return printer


@memoize_arg
def print_tuple(print_item):

    def printer(items):
        return '({},)'.format(', '.join(print_item(i) for i in items))

    return printer


# ----------------------------------------------------------------------------
# Abstraction

@memoize_arg
def max_free_ivar(code):
    assert is_code(code), code
    if is_atom(code) or is_nvar(code):
        return -1
    elif is_ivar(code):
        return code[1]
    elif is_app(code) or is_join(code):
        return max(max_free_ivar(code[1]), max_free_ivar(code[2]))
    else:
        raise NotImplementedError(code)


@memoize_args
def try_abstract(body):
    """APP,JOIN,I,K,B,C,S,eta abstraction algorithm for de Bruijn variables.

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
    elif is_join(body):
        lhs_found, lhs = try_abstract(body[1])
        rhs_found, rhs = try_abstract(body[2])
        if not lhs_found:
            if not rhs_found:
                return False, JOIN(lhs, rhs)  # Rule K
            else:
                assert lhs not in (BOT, TOP), body
                return True, JOIN(APP(K, lhs), rhs)  # Rule JOIN-K
        else:
            if not rhs_found:
                assert rhs not in (BOT, TOP), body
                return True, JOIN(lhs, APP(K, rhs))  # Rule JOIN-K
            else:
                return True, JOIN(lhs, rhs)  # Rule JOIN
    else:
        raise NotImplementedError(body)


def abstract(body):
    """APP,JOIN,TOP,BOT,I,K,B,C,S,eta-abstraction algorithm.

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
    elif is_join(body):
        lhs = code_increment_ivars(body[1], min_rank)
        rhs = code_increment_ivars(body[2], min_rank)
        return JOIN(lhs, rhs)
    else:
        raise NotImplementedError(body)


@memoize_args
def stack_increment_ivars(stack, min_rank):
    if stack is None:
        return None
    else:
        arg, stack = stack
        arg = cont_increment_ivars(arg, min_rank)
        stack = stack_increment_ivars(stack, min_rank)
        return arg, stack


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

INERT_ATOMS = frozenset([S])


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
def make_cont(type_, args):
    """Continuations are linear-beta-eta normal forms."""
    if type_ is CONT_TYPE_APP:
        assert isinstance(args, ContApp), args
        head, stack, bound = args
        assert is_ivar(head) or is_nvar(head) or head in INERT_ATOMS, head
        if head is S:
            assert stack is not None
            assert stack[1] is not None
            assert stack[1][1] is not None
            assert not is_cheap_to_copy(stack[1][1][0])
        else:
            assert is_ivar(head) or is_nvar(head)
        assert is_stack(stack), stack
        assert isinstance(bound, int) and bound >= 0, bound
    elif type_ is CONT_TYPE_JOIN:
        assert isinstance(args, tuple) and len(args) == 2, args
        lhs, rhs = args
        assert is_cont(lhs), lhs
        assert is_cont(rhs), rhs
    elif type_ is CONT_TYPE_TOP:
        assert args is None
    elif type_ is CONT_TYPE_BOT:
        assert args is None
    else:
        raise ValueError(type_)
    return Cont(type_, args)


def make_cont_app(head, stack, bound):
    assert is_code(head), head
    assert is_stack(stack), stack
    assert isinstance(bound, int) and bound >= 0, bound
    return make_cont(CONT_TYPE_APP, ContApp(head, stack, bound))


def make_cont_join(lhs, rhs):
    assert is_cont(lhs), lhs
    assert is_cont(rhs), rhs
    # TODO sort wrt priority
    return make_cont(CONT_TYPE_JOIN, (lhs, rhs))


CONT_BOT = make_cont(CONT_TYPE_BOT, None)
CONT_TOP = make_cont(CONT_TYPE_TOP, None)
CONT_IVAR_0 = make_cont_app(IVAR(0), None, 0)
CONT_TRUE = make_cont_app(IVAR(1), None, 2)
CONT_FALSE = make_cont_app(IVAR(0), None, 2)


@memoize_args
def cont_increment_ivars(cont, min_rank):
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        head, stack, bound = cont.args
        head = code_increment_ivars(head, min_rank + bound)
        stack = stack_increment_ivars(stack, min_rank + bound)
        return make_cont_app(head, stack, bound)
    elif cont.type is CONT_TYPE_JOIN:
        lhs, rhs = cont.args
        lhs = cont_increment_ivars(lhs, min_rank)
        rhs = cont_increment_ivars(rhs, min_rank)
        return make_cont_join(lhs, rhs)
    elif cont.type is CONT_TYPE_TOP:
        return cont
    elif cont.type is CONT_TYPE_BOT:
        return cont
    else:
        raise ValueError(cont)


def cont_iter_join(cont):
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_JOIN:
        for arg in cont.args:
            for part in cont_iter_join(arg):
                yield part
    elif cont.type is not CONT_TYPE_BOT:
        yield cont


# ----------------------------------------------------------------------------
# Conversion : code -> continuation

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


def is_head_normal(cont):
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        head = cont.args.head
        return is_ivar(head) or is_nvar(head)
    elif cont.type is CONT_TYPE_JOIN:
        lhs, rhs = cont.args
        return is_head_normal(lhs) and is_head_normal(rhs)
    elif cont.type is CONT_TYPE_TOP:
        return True
    else:
        raise ValueError(cont)


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
            arg = cont_from_codes((self.head[2],))
            self.stack = arg, self.stack
            self.head = self.head[1]
        return self.head

    def peek_at_arg(self, pos):
        assert isinstance(pos, int) and pos > 0
        stack = self.stack
        for _ in xrange(pos):
            if stack is None:
                return CONT_IVAR_0
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
                args = [cont_increment_ivars(arg, 0) for arg in args]
                args.append(CONT_IVAR_0)
                self.bound += 1
        return args

    def push_arg(self, arg):
        assert is_cont(arg), arg
        self.stack = arg, self.stack

    def freeze(self):
        if self.head is TOP:
            return CONT_TOP
        else:
            # TODO eta contract, compensating for expansion in .pop_args().
            return make_cont_app(self.head, self.stack, self.bound)


class TopError(Exception):
    pass


@logged(print_tuple(print_code), print_stack, str, returns=print_cont)
@memoize_args
def cont_from_codes(codes, stack=None, bound=0):  # DEPRECATED
    assert all(map(is_code, codes)), codes
    pending = [PreContinuation(code, stack, bound) for code in codes]
    result = set()
    while pending:
        precont = pending.pop()
        head = precont.seek_head()

        if is_ivar(head) or is_nvar(head):
            result.add(precont.freeze())
            continue
        elif head is TOP:
            return CONT_TOP
        elif head is BOT:
            continue
        elif head is I:
            x, = precont.pop_args(1)
            head_cont = x
        elif head is K:
            x, y = precont.pop_args(2)
            head_cont = x
        elif head is B:
            x, y, z = precont.pop_args(3)
            yz = cont_app(y, z)
            precont.push_arg(yz)
            head_cont = x
        elif head is C:
            x, y, z = precont.pop_args(3)
            precont.push_arg(y)
            precont.push_arg(z)
            head_cont = x
        elif head is S:
            z = precont.peek_at_arg(3)
            if not is_cheap_to_copy(z):
                # TODO simplify S x y, to see if it is linear.
                result.add(precont.freeze())
                continue
            x, y, z = precont.pop_args(3)
            yz = cont_app(y, z)
            precont.push_arg(yz)
            precont.push_arg(z)
            head_cont = x
        elif is_join(head):
            lhs = cont_from_codes((head[1],))
            rhs = cont_from_codes((head[2],))
            head_cont = join_conts(set([lhs, rhs]))
        else:
            raise NotImplementedError(head)

        stack = precont.stack
        bound = precont.bound
        for cont in cont_iter_join(head_cont):
            head = cont_to_code(cont)
            pending.append(PreContinuation(head, stack, bound))

    return join_conts(result)


@logged(print_cont, print_cont, returns=print_cont)
def cont_app(fun, arg):
    """Returns a cont."""
    assert is_cont(fun), fun
    assert is_cont(arg), arg
    codes = tuple(sorted(cont_to_code(part) for part in cont_iter_join(fun)))
    stack = arg, None
    return cont_from_codes(codes, stack)


# ----------------------------------------------------------------------------
# Conversion : continuation -> code

@logged(print_cont, returns=print_code)
@memoize_arg
def cont_to_code(cont):
    """Returns code in linear normal form.

    Desired Theorem: For any cont,
      cont_from_codes((cont_to_code(cont),)) == cont

    """
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        head, stack, bound = cont.args
        while stack is not None:
            arg_cont, stack = stack
            arg_code = cont_to_code(arg_cont)
            head = APP(head, arg_code)
        for _ in xrange(bound):
            head = abstract(head)
        return head
    elif cont.type is CONT_TYPE_JOIN:
        codes = map(cont_to_code, cont_iter_join(cont))
        return join_codes(codes)
    elif cont.type is CONT_TYPE_TOP:
        return TOP
    elif cont.type is CONT_TYPE_BOT:
        return BOT
    else:
        raise ValueError(cont)


@logged(print_set(print_code), returns=print_code)
def join_codes(codes):
    assert isinstance(codes, list)
    assert all(map(is_code, codes)), codes
    if not codes:
        return BOT
    codes.sort(key=lambda code: (complexity(code), code))
    result = codes[0]
    for code in codes[1:]:
        result = JOIN(result, code)
    return result


@logged(print_set(print_cont), returns=print_cont)
def join_conts(conts):
    """Joins a set of conts into a single cont, simplifying via heuristics."""
    assert isinstance(conts, set), conts
    if not conts:
        return CONT_BOT

    # Destructure all JOIN terms.
    parts = map(cont_iter_join, conts)
    conts = set(itertools.chain(*parts))
    if not conts:
        return CONT_BOT
    if len(conts) == 1:
        return next(iter(conts))

    # Filter out dominated conts.
    filtered_conts = [
        cont for cont in conts
        if not any(cont_dominates(ub, cont) for ub in conts if ub is not cont)
    ]

    # TODO rearrange binary join operator in order of compute_step priority,
    #  so as to minimize list thrashing.
    filtered_conts.sort(key=lambda cont: (cont_complexity(cont), cont))

    # Construct a join term.
    result = filtered_conts[0]
    for cont in filtered_conts[1:]:
        result = make_cont_join(result, cont)
    return result


# ----------------------------------------------------------------------------
# Decision procedures

@logged(print_code, print_code, returns=str)
def try_decide_less(lhs, rhs):
    """Sound incomplete decision procedure for Scott ordering between codes.

    Args: lhs, rhs must be codes.
    Returns: True, False, or None.

    """
    assert is_code(lhs), lhs
    assert is_code(rhs), rhs
    lhs_term = cont_from_codes((lhs,))
    rhs_term = cont_from_codes((rhs,))
    return cont_try_decide_less(lhs_term, rhs_term)


@logged(print_cont, print_cont, returns=str)
@memoize_args
def cont_try_decide_less(lhs, rhs):
    """Weak decision oracle for Scott ordering.

         | TOP   IVAR   NVAR   S
    -----+---------------------------
     TOP | True  False  None   approx
    IVAR | True  delta  False  approx
    NVAR | True  False  ...    approx
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

    Args:
        lhs, rhs : cont
    Returns:
        True, False, or None

    """
    assert is_cont(lhs), lhs
    assert is_cont(rhs), rhs

    # Try simple cases.
    if lhs is CONT_BOT or lhs is rhs or rhs is CONT_TOP:
        return True

    # Destructure lhs.
    if lhs.type is CONT_TYPE_APP:
        lhs_head, lhs_stack, lhs_bound = lhs.args
    elif lhs.type is CONT_TYPE_JOIN:
        return trool_all(
            cont_try_decide_less(lhs_part, rhs)
            for lhs_part in cont_iter_join(lhs)
        )
    elif lhs.type is CONT_TYPE_TOP:
        lhs_head, lhs_stack, lhs_bound = TOP, None, 0
    else:
        raise ValueError(lhs)

    # Destructure rhs.
    if rhs.type is CONT_TYPE_APP:
        rhs_head, rhs_stack, rhs_bound = rhs.args
    elif rhs.type is CONT_TYPE_JOIN:
        return trool_any(
            cont_try_decide_less(lhs, rhs_part)
            for rhs_part in cont_iter_join(rhs)
        )
    elif rhs.type is CONT_TYPE_BOT:
        rhs_head, rhs_stack, rhs_bound = BOT, None, 0
    else:
        raise ValueError(lhs)

    # Try incompatible cases.
    if lhs_head is TOP and rhs_head is BOT:
        return False
    if lhs_head is TOP and is_ivar(rhs_head):
        return False
    if is_ivar(lhs_head) and rhs_head is BOT:
        return False

    # Eta expand until binder counts agree.
    for _ in xrange(rhs_bound - lhs_bound):
        lhs_head = code_increment_ivars(lhs_head, 0)
        lhs_stack = stack_increment_ivars(lhs_stack, 0)
    for _ in xrange(lhs_bound - rhs_bound):
        rhs_head = code_increment_ivars(rhs_head, 0)
        rhs_stack = stack_increment_ivars(rhs_stack, 0)

    # Check for unknowns.
    if is_nvar(lhs_head) or is_nvar(rhs_head):
        if lhs_head is rhs_head:
            return stack_try_decide_less(lhs_stack, rhs_stack)
        return None

    # Try comparing stacks.
    assert is_ivar(lhs_head) or lhs_head in INERT_ATOMS, lhs_head
    assert is_ivar(rhs_head) or rhs_head in INERT_ATOMS, rhs_head
    if is_ivar(lhs_head) and is_ivar(rhs_head):
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
        cont_try_decide_less(lhs_arg, rhs_arg)
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


def dominates(lhs, rhs):
    lhs_rhs = try_decide_less(lhs, rhs)
    rhs_lhs = try_decide_less(rhs, lhs)
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
            yield cont_from_codes((head,), stack, bound)
    elif cont.type is CONT_TYPE_JOIN:
        parts = [
            iter_head_upper_bounds(part)
            for part in cont_iter_join(cont)
        ]
        for heads in itertools.product(*parts):
            yield cont_from_codes(heads, stack, bound)
    elif cont.type is CONT_TYPE_TOP:
        yield CONT_TOP
    elif cont.type is CONT_TYPE_BOT:
        yield CONT_BOT
    else:
        raise ValueError(cont)


def iter_head_lower_bounds(cont):
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        head, stack, bound = cont.args
        assert head is S, cont
        cont_lb = cont_from_codes(S_LINEAR_LOWER_BOUNDS, stack, bound)
        for part_lb in cont_iter_join(cont_lb):
            yield part_lb
    elif cont.type is CONT_TYPE_JOIN:
        parts = [
            iter_head_lower_bounds(part)
            for part in cont_iter_join(cont)
        ]
        for heads in itertools.product(*parts):
            yield cont_from_codes(heads, stack, bound)
    elif cont.type is CONT_TYPE_TOP:
        yield CONT_TOP
    elif cont.type is CONT_TYPE_BOT:
        yield CONT_BOT
    else:
        raise ValueError(cont)


# ----------------------------------------------------------------------------
# Reduction

@memoize_arg
def stack_try_compute_step(stack):
    if stack is None:
        return False, None
    cont, stack = stack
    progress, cont = cont_try_compute_step(cont)
    if not progress:
        progress, stack = stack_try_compute_step(stack)
    stack = cont, stack
    return progress, stack


@memoize_arg
def cont_try_compute_step(cont):
    """Returns a cont."""
    assert is_cont(cont), cont
    if cont.type is CONT_TYPE_APP:
        precont = PreContinuation(*cont.args)
        head = precont.seek_head()
        progress = False
        if head is S:
            x, y, z = precont.pop_args(3)
            assert not is_cheap_to_copy(z), z
            yz = cont_app(y, z)
            precont.push_arg(yz)
            precont.push_arg(z)
            codes = tuple(sorted(map(cont_to_code, x)))  # FIXME
            cont = cont_from_codes(codes, precont.stack, precont.bound)
            return True, cont
        else:
            assert is_ivar(head) or is_nvar(head), head
        if not progress:
            progress, precont.stack = stack_try_compute_step(precont.stack)
        if progress:
            codes = (head,)
            cont = cont_from_codes(codes, precont.stack, precont.bound)
        return progress, cont
    elif cont.type is CONT_TYPE_JOIN:
        parts = list(cont_iter_join(cont))
        for i, part in enumerate(parts):
            progress, part = cont_try_compute_step(part)
            if progress:
                parts[i] = part
                return True, join_conts(set(parts))
        return False, cont
    elif cont.type is CONT_TYPE_TOP:
        return False, CONT_TOP
    elif cont.type is CONT_TYPE_BOT:
        return False, CONT_BOT
    else:
        raise ValueError(cont)


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
    elif cont.type is CONT_TYPE_TOP:
        return 0
    elif cont.type is CONT_TYPE_BOT:
        return 0
    else:
        raise ValueError(cont)


def priority(cont):
    return cont_complexity(cont), cont  # Deterministically break ties.


def cont_is_normal(cont):
    assert is_cont(cont), cont
    progress, cont = cont_try_compute_step(cont)
    return not progress


@logged(print_code, returns=print_code)
@memoize_arg
def compute(code):
    assert is_code(code), code
    cont = cont_from_codes((code,))
    working = True
    while working:
        working, cont = cont_try_compute_step(cont)
    cont = join_conts(set(
        c for c in cont_iter_join(cont) if cont_is_normal(c)
    ))
    return cont_to_code(cont)


def reduce(code, budget=0):
    """Beta-eta reduce code, ignoring budget."""
    assert is_code(code), code
    assert isinstance(budget, int) and budget >= 0, budget
    LOG.info('reduce({})'.format(pretty(code)))
    code = compute(code)
    assert max_free_ivar(code) < 0, code
    return code


def simplify(code):
    """Linearly beta-eta reduce."""
    assert is_code(code), code
    LOG.info('simplify({})'.format(pretty(code)))
    cont = cont_from_codes((code,))
    code = cont_to_code(cont)
    assert max_free_ivar(code) < 0, code
    return code