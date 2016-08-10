from collections import namedtuple
from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
from pomagma.reducer import oracle
from pomagma.reducer.code import VAR, APP, TOP, BOT, I, K, B, C, S, J, EVAL
from pomagma.reducer.code import free_vars, complexity
from pomagma.reducer.code import is_var, is_app, is_quote
from pomagma.reducer.code import sexpr_print as print_code
from pomagma.reducer.sugar import abstract
from pomagma.reducer.util import logged
from pomagma.reducer.util import LOG
from pomagma.reducer.util import PROFILE_COUNTERS
from pomagma.reducer.util import pretty
import itertools

__all__ = ['reduce', 'simplify']

F = APP(K, I)
true = K
false = F


def iter_shared_list(shared_list):
    while shared_list is not None:
        arg, shared_list = shared_list
        yield arg


@memoize_arg
def make_var(n):
    return VAR('v{}'.format(n))


def fresh(avoid):
    """Return the smallest variable not in avoid."""
    PROFILE_COUNTERS[fresh, len(avoid)] += 1
    for i in itertools.count():
        var = make_var(i)
        if var not in avoid:
            return var


def join_codes(codes):
    """Joins a set of codes into a single code, simplifying via heuristics."""
    assert isinstance(codes, set)
    if not codes:
        return BOT

    # Apply J-eta rules to recognize J and APP(J, x).
    # This should really be combined with _close.
    if K in codes and F in codes:
        codes.remove(K)
        codes.remove(F)
        codes.add(J)
    if I in codes:
        for kx in tuple(codes):
            if is_app(kx) and kx[1] is K:
                codes.discard(I)
                codes.remove(kx)
                codes.add(APP(J, kx[2]))

    # Filter out dominated codes.
    # FIXME If x [= y and y [= x, this filters out both.
    filtered_codes = []
    for code in codes:
        if not any(oracle.try_decide_less(code, other)
                   for other in codes
                   if other is not code):
            filtered_codes.append(code)
    filtered_codes.sort(key=lambda code: (complexity(code), code))

    # Construct a join term.
    result = filtered_codes[0]
    for code in filtered_codes[1:]:
        result = APP(APP(J, result), code)
    return result


# ----------------------------------------------------------------------------
# Tracing

def print_stack(stack):
    return '[{}]'.format(
        ', '.join(print_cont_set(v) for v in iter_shared_list(stack)))


def print_bound(bound):
    return '[{}]'.format(', '.join(v[1] for v in iter_shared_list(bound)))


def print_cont(cont):
    return '{} {} {}'.format(
        print_code(cont.head),
        print_stack(cont.stack),
        print_bound(cont.bound),
    )


def print_cont_set(cont_set):
    return '{{{}}}'.format(', '.join(print_cont(c) for c in cont_set))


def print_code_set(code_set):
    return '{{{}}}'.format(', '.join(print_code(c) for c in code_set))


def print_tuple(*printers):

    def printer(args):
        assert len(args) <= len(printers), args
        return ', '.join(p(a) for a, p in itertools.izip(args, printers))

    return printer


# ----------------------------------------------------------------------------
# Continuations

# head : code
# stack : stack (frozenset continuation)
# bound : stack var
Continuation = namedtuple('Continuation', ['head', 'stack', 'bound'])


@memoize_args
def make_cont(head, stack, bound):
    """Continuations are linear-beta-eta normal forms."""
    assert is_var(head) or head in (TOP, BOT, S, EVAL), head
    if head in (TOP, BOT):
        assert stack is None and bound is None
    elif head is S:
        assert not (
            stack and stack[1] and stack[1][1] and
            is_cheap_to_copy(stack[1][1][0]))
    elif head is EVAL:
        assert not (stack and is_quote(stack[0]))
    return Continuation(head, stack, bound)


@memoize_arg
def make_cont_set(cont_set):
    # TODO filter out dominated continuations
    assert isinstance(cont_set, frozenset), cont_set
    assert all(isinstance(c, Continuation) for c in cont_set)
    return cont_set


CONT_TOP = make_cont(TOP, None, None)
CONT_SET_TOP = make_cont_set(frozenset([CONT_TOP]))


@logged(print_cont, returns=print_code)
@memoize_arg
def cont_eval(cont):
    """Returns code in linear normal form."""
    assert isinstance(cont, Continuation)
    head, stack, bound = cont
    while stack is not None:
        arg_cont_set, stack = stack
        arg_code = cont_set_eval(arg_cont_set)
        head = APP(head, arg_code)
    while bound is not None:
        var, bound = bound
        head = abstract(var, head)
    return head


@logged(print_cont_set, returns=print_code)
@memoize_arg
def cont_set_eval(cont_set):
    """Returns code in linear normal form."""
    assert isinstance(cont_set, frozenset)
    assert all(isinstance(c, Continuation) for c in cont_set)
    codes = set(map(cont_eval, cont_set))
    return join_codes(codes)


def cont_free_vars(cont):
    all_vars = free_vars(cont.head)
    for cont_set in iter_shared_list(cont.stack):
        all_vars |= cont_set_free_vars(cont_set)
    bound_vars = frozenset(iter_shared_list(cont.bound))
    return all_vars - bound_vars


def cont_set_free_vars(cont_set):
    free = frozenset()
    for cont in cont_set:
        free |= cont_free_vars(cont)
    return free


@logged(print_stack, print_bound,
        print_cont_set, print_cont_set, print_cont_set,
        returns=print_tuple(print_cont_set, print_stack, print_bound))
def pop_arg(stack, bound, *cont_sets):
    if stack is not None:
        cont_set, stack = stack
        return cont_set, stack, bound
    else:
        avoid = frozenset()
        for cont_set in cont_sets:
            avoid |= cont_set_free_vars(cont_set)
        var = fresh(avoid)
        bound = var, bound
        cont = make_cont(var, None, None)
        cont_set = make_cont_set(frozenset([cont]))
        return cont_set, stack, bound


@logged(print_cont_set, print_cont_set, returns=print_cont_set)
def cont_app(funs, args):
    assert isinstance(funs, frozenset)
    assert isinstance(args, frozenset)
    assert all(isinstance(f, Continuation) for f in funs)
    assert all(isinstance(a, Continuation) for a in args)
    codes = tuple(map(cont_eval, funs))
    stack = args, None
    return cont_set_from_codes(codes, stack)


def is_cheap_to_copy(cont_set):
    assert isinstance(cont_set, frozenset)
    assert all(isinstance(c, Continuation) for c in cont_set)
    if len(cont_set) > 1:
        return False
    for cont in cont_set:
        # TODO this could instead check is_linear(cont)
        if cont.stack or cont.bound:
            return False
        head = cont.head
        if not (is_var(head) or head is TOP or head is BOT):
            return False
    return True


@logged(print_code_set, print_stack, print_bound, returns=print_cont_set)
@memoize_args
def cont_set_from_codes(codes, stack=None, bound=None):
    pending = [(code, stack, bound) for code in codes]
    result = []
    while pending:
        head, stack, bound = pending.pop()
        while is_app(head):
            arg_cont = cont_set_from_codes((head[2],))
            stack = arg_cont, stack
            head = head[1]

        if is_var(head):
            result.append(make_cont(head, stack, bound))
            continue
        elif head is TOP:
            return CONT_SET_TOP
        elif head is BOT:
            continue
        elif head is I:
            x, stack, bound = pop_arg(stack, bound)
            head_cont = x
        elif head is K:
            x, stack, bound = pop_arg(stack, bound)
            y, stack, bound = pop_arg(stack, bound, x)
            head_cont = x
        elif head is B:
            x, stack, bound = pop_arg(stack, bound)
            y, stack, bound = pop_arg(stack, bound, x)
            z, stack, bound = pop_arg(stack, bound, x, y)
            yz = cont_app(y, z)
            stack = yz, stack
            head_cont = x
        elif head is C:
            x, stack, bound = pop_arg(stack, bound)
            y, stack, bound = pop_arg(stack, bound, x)
            z, stack, bound = pop_arg(stack, bound, x, y)
            stack = y, stack
            stack = z, stack
            head_cont = x
        elif head is S:
            old_stack = stack
            old_bound = bound
            x, stack, bound = pop_arg(stack, bound)
            y, stack, bound = pop_arg(stack, bound, x)
            z, stack, bound = pop_arg(stack, bound, x, y)
            if is_cheap_to_copy(z):
                yz = cont_app(y, z)
                stack = yz, stack
                stack = z, stack
                head_cont = x
            else:
                result.append(make_cont(S, old_stack, old_bound))
                continue
        elif head is J:
            x, stack, bound = pop_arg(stack, bound)
            y, stack, bound = pop_arg(stack, bound, x)
            head_cont = x | y
        elif head is EVAL:
            old_stack = stack
            old_bound = bound
            x, stack, bound = pop_arg(stack, bound)
            x = cont_set_eval(x)
            if is_quote(x):
                head = x[1]
            elif x is TOP:
                return CONT_SET_TOP
            elif x is BOT:
                continue
            else:
                result.append(make_cont(EVAL, old_stack, old_bound))
                continue
        else:
            raise NotImplementedError(head)

        for cont in head_cont:
            pending.append((cont_eval(cont), stack, bound))

    return make_cont_set(frozenset(result))


@logged(print_stack, returns=print_tuple(str, print_stack))
@memoize_arg
def stack_try_compute_step(stack):
    if stack is None:
        return False, None
    cont_set, stack = stack
    success, cont_set = cont_set_try_compute_step(cont_set)
    if success:
        return True, cont_set
    success, stack = stack_try_compute_step(stack)
    stack = cont_set, stack
    return success, stack


@logged(print_cont, returns=print_tuple(str, print_cont_set))
@memoize_arg
def cont_try_compute_step(cont):
    assert isinstance(cont, Continuation)
    head, stack, bound = cont
    if head is S:
        x, stack, bound = pop_arg(stack, bound)
        y, stack, bound = pop_arg(stack, bound, x)
        z, stack, bound = pop_arg(stack, bound, x, y)
        assert not is_cheap_to_copy(z), z
        yz = cont_app(y, z)
        stack = yz, stack
        stack = z, stack
        codes = tuple(map(cont_eval, x))
        cont_set = cont_set_from_codes(codes, stack, bound)
        success = True
    else:
        assert is_var(head) or head in (TOP, BOT, EVAL), head
        success, stack = stack_try_compute_step(stack)
        if success:
            cont = make_cont(head, stack, bound)
        cont_set = make_cont_set(frozenset([cont]))
    return success, cont_set


def cont_complexity(cont):
    assert isinstance(cont, Continuation)
    result = complexity(cont.head)
    for arg in iter_shared_list(cont.stack):
        result += 1 + complexity(arg)  # APP(-, arg)
    for var in iter_shared_list(cont.bound):
        result += 1 + complexity(var)  # FUN(var, -)
    return result


@logged(print_cont_set, returns=print_tuple(str, print_cont_set))
@memoize_arg
def cont_set_try_compute_step(cont_set):
    assert isinstance(cont_set, frozenset)
    assert all(isinstance(c, Continuation) for c in cont_set)
    # TODO Separate cont_set into seen and pending.
    for cont in sorted(cont_set, key=cont_complexity):
        success, new_cont_set = cont_try_compute_step(cont)
        if success and not new_cont_set <= cont_set:
            return True, make_cont_set(cont_set | new_cont_set)
    return False, cont_set


def cont_is_normal(cont):
    assert isinstance(cont, Continuation)
    success, cont_set = cont_try_compute_step(cont)
    return not success


@logged(print_code, returns=print_code)
@memoize_arg
def compute(code):
    cont_set = cont_set_from_codes((code,))
    working = True
    while working:
        working, cont_set = cont_set_try_compute_step(cont_set)
    cont_set = make_cont_set(frozenset(
        c for c in cont_set if cont_is_normal(c)
    ))
    return cont_set_eval(cont_set)


def reduce(code, budget=0):
    '''Beta-eta reduce code, ignoring budget.'''
    assert isinstance(budget, int) and budget >= 0, budget
    LOG.info('reduce({})'.format(pretty(code)))
    return compute(code)


def simplify(code):
    '''Linearly beta-eta reduce.'''
    LOG.info('simplify({})'.format(pretty(code)))
    cont_set = cont_set_from_codes((code,))
    return cont_set_eval(cont_set)
