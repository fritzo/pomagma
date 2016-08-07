__all__ = ['reduce', 'simplify']

from collections import namedtuple
from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
from pomagma.reducer import oracle
from pomagma.reducer.code import CODE, EVAL, QQUOTE, QAPP, EQUAL, LESS
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, J
from pomagma.reducer.code import UNIT, BOOL, MAYBE
from pomagma.reducer.code import VAR, APP, QUOTE
from pomagma.reducer.code import free_vars, complexity
from pomagma.reducer.code import is_var, is_atom, is_app, is_quote
from pomagma.reducer.sugar import abstract
from pomagma.reducer.util import LOG
from pomagma.reducer.util import PROFILE_COUNTERS
from pomagma.reducer.util import logged
from pomagma.reducer.util import pretty
import heapq
import itertools

F = APP(K, I)
true = K
false = F


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


# ----------------------------------------------------------------------------
# Continuations

# head : code
# stack : stack (frozenset continuation)
# bound : stack var
Continuation = namedtuple('Continuation', ['head', 'stack', 'bound'])


@memoize_args
def make_cont(head, stack, bound):
    assert is_var(head) or head in (TOP, BOT, S), head
    if head in (TOP, BOT):
        assert stack is None and bound is None
    return Continuation(head, stack, bound)


@memoize_arg
def make_cont_set(cont_set):
    # TODO filter out dominated continuations
    assert isinstance(cont_set, frozenset), cont_set
    assert all(isinstance(c, Continuation) for c in cont_set)
    return cont_set


CONT_TOP = make_cont(TOP, None, None)
CONT_SET_TOP = make_cont_set(frozenset([CONT_TOP]))


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


@memoize_arg
def cont_set_eval(cont_set):
    """Returns code in linear normal form."""
    assert isinstance(cont_set, frozenset)
    assert all(isinstance(c, Continuation) for c in cont_set)
    codes = set(map(cont_eval, cont_set))
    return join_codes(codes)


def pop_arg(stack, bound, *terms):
    if stack is not None:
        cont_set, stack = stack
        return cont_set, stack, bound
    else:
        avoid = frozenset()
        for term in terms:
            avoid |= free_vars(term)
        var = fresh(avoid)
        bound = var, bound
        cont = make_cont(var, None, None)
        cont_set = make_cont_set(frozenset([cont]))
        return cont_set, stack, bound


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

        for cont in head_cont:
            pending.append((cont_eval(cont), stack, bound))

    return make_cont_set(frozenset(result))


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


@memoize_arg
def cont_try_compute_step(cont):
    assert isinstance(cont, Continuation)
    head, stack, bound = cont
    if head is S:
        x, stack, bound = pop_arg(stack, bound)
        y, stack, bound = pop_arg(stack, bound, x)
        z, stack, bound = pop_arg(stack, bound, x, y)
        yz = cont_app(y, z)
        stack = yz, stack
        stack = z, stack
        codes = tuple(map(cont_eval, x))
        cont_set = cont_set_from_codes(codes, stack, bound)
        success = True
    else:
        success, stack = stack_try_compute_step(stack)
        if success:
            cont = make_cont(head, stack, bound)
        cont_set = make_cont_set(frozenset([cont]))
    return success, cont_set


@memoize_arg
def cont_set_try_compute_step(cont_set):
    assert isinstance(cont_set, frozenset)
    assert all(isinstance(c, Continuation) for c in cont_set)
    for cont in sorted(cont_set, key=cont_complexity):
        success, new_cont_set = cont_try_compute_step(cont)
        if success and not new_cont_set <= cont_set:
            return True, make_cont_set(cont_set | new_cont_set)
    return False, cont_set


def cont_is_normal(cont):
    assert isinstance(cont, Continuation)
    success, cont_set = cont_try_compute_step(cont)
    return not success


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


def cont_complexity(cont):
    assert isinstance(cont, Continuation)
    result = complexity(cont.head)
    for arg in iter_shared_list(cont.stack):
        result += 1 + complexity(arg)  # APP(-, arg)
    for var in iter_shared_list(cont.bound):
        result += 1 + complexity(var)  # FUN(var, -)
    return result


# ----------------------------------------------------------------------------
# Immutable shared contexts

Context = namedtuple('Context', ['stack', 'bound'])
EMPTY_CONTEXT = Context(None, None)


def context_pop(context, *terms):
    if context.stack is not None:
        arg, stack = context.stack
        return arg, Context(stack, context.bound)
    else:
        avoid = frozenset()
        for term in terms:
            avoid |= free_vars(term)
        arg = fresh(avoid)
        bound = arg, context.bound
        return arg, Context(context.stack, bound)


def context_push(context, arg):
    stack = arg, context.stack
    return Context(stack, context.bound)


def iter_shared_list(shared_list):
    while shared_list is not None:
        arg, shared_list = shared_list
        yield arg


def context_complexity(context):
    result = 0
    for arg in iter_shared_list(context.stack):
        result += 1 + complexity(arg)  # APP(-, arg)
    for var in iter_shared_list(context.bound):
        result += 1 + complexity(var)  # FUN(var, -)
    return result


def continuation_complexity(continuation):
    head, context = continuation
    return complexity(head) + context_complexity(context)


# ----------------------------------------------------------------------------
# Priority queue for concurrent continuations

class ContinuationQueue(object):
    """Complexity-prioritized uniqueness-filtered continuation scheduler.

    The lowest-complexity continuation is executed first.
    Duplicates may be scheduled, but will only be executed once.
    Uniqueness filtering has the nice effect of detecting some loops.
    """
    __slots__ = ['_to_pop', '_pushed']

    def __init__(self):
        self._to_pop = []
        self._pushed = set()

    def schedule(self, continuation):
        if continuation not in self._pushed:
            self._pushed.add(continuation)
            priority = continuation_complexity(continuation)
            heapq.heappush(self._to_pop, (priority, continuation))

    def __iter__(self):
        return self

    def __next__(self):
        try:
            priority_task = heapq.heappop(self._to_pop)
        except IndexError:
            raise StopIteration
        return priority_task[1]

    next = __next__  # next() for python 2, __next__ for python 3.


# ----------------------------------------------------------------------------
# Reduction

def try_unquote(code):
    return code[1] if is_quote(code) else None


TROOL_TO_CODE = {
    True: true,
    False: false,
    None: None,
}

TRY_DECIDE = {
    EQUAL: oracle.try_decide_equal,
    LESS: oracle.try_decide_less,
}

TRY_CAST = {
    BOOL: oracle.try_cast_bool,
    UNIT: oracle.try_cast_unit,
    MAYBE: oracle.try_cast_maybe,
    CODE: oracle.try_cast_code,
}


def _sample(head, context, nonlinear):
    """FIFO-scheduled sampler."""
    # Head reduce.
    while True:
        # LOG.debug('head = {}'.format(pretty(head)))
        PROFILE_COUNTERS[
            _sample, head[0] if isinstance(head, tuple) else head] += 1
        if is_app(head):
            context = context_push(context, head[2])
            head = head[1]
        elif is_var(head):
            yield head, context
            return
        elif is_quote(head):
            x = head[1]
            x = _reduce(x, False)
            head = QUOTE(x)
            yield head, context
            return
        elif head is TOP:
            yield TOP, EMPTY_CONTEXT
            return
        elif head is BOT:
            return
        elif head is I:
            head, context = context_pop(context)
        elif head is K:
            x, context = context_pop(context)
            y, context = context_pop(context, x)
            head = x
        elif head is B:
            x, context = context_pop(context)
            y, context = context_pop(context, x)
            z, context = context_pop(context, x, y)
            head = x
            context = context_push(context, _app(y, z, False))
        elif head is C:
            x, context = context_pop(context)
            y, context = context_pop(context, x)
            z, context = context_pop(context, x, y)
            head = x
            context = context_push(context, y)
            context = context_push(context, z)
        elif head is S:
            old_context = context
            x, context = context_pop(context)
            y, context = context_pop(context, x)
            z, context = context_pop(context, x, y)
            if nonlinear or is_var(z):
                head = x
                context = context_push(context, _app(y, z, False))
                context = context_push(context, z)
            else:
                yield head, old_context
                return
        elif head is J:
            x, context = context_pop(context)
            y, context = context_pop(context, x)
            for head in (x, y):
                for continuation in _sample(head, context, nonlinear):
                    yield continuation
        elif head is EVAL:
            x, context = context_pop(context)
            x = _reduce(x, nonlinear)
            if is_quote(x):
                head = x[1]
            elif x is TOP:
                yield TOP, EMPTY_CONTEXT
                return
            elif x is BOT:
                return
            else:
                head = APP(EVAL, x)
                yield head, context
                return
        elif head is QQUOTE:
            x, context = context_pop(context)
            x = _reduce(x, nonlinear)
            if x is TOP:
                yield TOP, EMPTY_CONTEXT
                return
            elif x is BOT:
                return
            elif is_quote(x):
                head = QUOTE(x)
            else:
                head = APP(QQUOTE, x)
                yield head, context
                return
        elif head is QAPP:
            x, context = context_pop(context)
            y, context = context_pop(context, x)
            x = _reduce(x, nonlinear)
            y = _reduce(y, nonlinear)
            if is_quote(x) and is_quote(y):
                head = QUOTE(_app(x[1], y[1], False))
            else:
                head = APP(APP(QAPP, x), y)
                yield head, context
                return
        elif head in TRY_DECIDE:
            pred = head
            x, context = context_pop(context)
            y, context = context_pop(context, x)
            x = _reduce(x, nonlinear)
            y = _reduce(y, nonlinear)
            if x is TOP or y is TOP:
                yield TOP, EMPTY_CONTEXT
                return
            if x is BOT and y is BOT:
                return
            if pred is EQUAL:
                if (x is BOT and is_quote(y)) or (is_quote(x) and y is BOT):
                    return
            # FIXME This sometimes fails to err when it should; see (B3).
            # FIXME This could be stronger by nonlinearly reducing the
            #   arguments inside QUOTE(-) of the quoted terms; see (B4).
            answer = TRY_DECIDE[pred](try_unquote(x), try_unquote(y))
            head = TROOL_TO_CODE[answer]
            if head is None:
                head = APP(APP(pred, x), y)
                yield head, context
                return
        elif head in TRY_CAST:
            type_ = head
            x, context = context_pop(context)
            x = _reduce(x, nonlinear)
            while is_app(x) and x[1] is type_:
                x = x[2]
            head = TRY_CAST[type_](x)
            if head is None:
                head = APP(type_, x)
                yield head, context
                return
        else:
            raise ValueError(head)


def _schedule(head, context, queue):
    for continuation in _sample(head, context, False):
        queue.schedule(continuation)


def _sample_nonlinear(head, context):
    """Fair priority-scheduled nonlinear sampler."""
    queue = ContinuationQueue()
    _schedule(head, context, queue)
    for head, context in queue:
        if head is S:
            x, context = context_pop(context)
            y, context = context_pop(context)
            z, context = context_pop(context)
            assert not is_var(z), 'missed optimization'
            head = x
            context = context_push(context, _app(y, z, False))
            context = context_push(context, z)
            _schedule(head, context, queue)
        else:
            yield head, context


def _close(continuation, nonlinear):
    """Close a continuation in linear-beta-eta normal form."""
    head, context = continuation
    PROFILE_COUNTERS[_close, head[0] if isinstance(head, tuple) else head] += 1

    # Reduce args.
    for arg in iter_shared_list(context.stack):
        # LOG.debug('head = {}'.format(pretty(head)))
        arg = _reduce(arg, nonlinear)
        head = APP(head, arg)

    # Abstract free variables.
    for var in iter_shared_list(context.bound):
        # LOG.debug('head = {}'.format(pretty(head)))
        head = abstract(var, head)

    return head


def _join(continuations, nonlinear):
    PROFILE_COUNTERS[_join, '...'] += 1

    # Collect unique samples.
    samples = set()
    for continuation in continuations:
        sample = _close(continuation, nonlinear)
        if sample is TOP:
            return TOP
        samples.add(sample)
    return join_codes(samples)


def join_codes(samples):
    """Joins a set of codes into a single code, simplifying via heuristics."""
    assert isinstance(samples, set)
    if not samples:
        return BOT

    # Apply J-eta rules to recognize J and APP(J, x).
    # This should really be combined with _close.
    if K in samples and F in samples:
        samples.remove(K)
        samples.remove(F)
        samples.add(J)
    if I in samples:
        for kx in tuple(samples):
            if is_app(kx) and kx[1] is K:
                samples.discard(I)
                samples.remove(kx)
                samples.add(APP(J, kx[2]))

    # Filter out dominated samples.
    # FIXME If x [= y and y [= x, this filters out both.
    filtered_samples = []
    for sample in samples:
        if not any(oracle.try_decide_less(sample, other)
                   for other in samples
                   if other is not sample):
            filtered_samples.append(sample)
    filtered_samples.sort(key=lambda code: (complexity(code), code))

    # Construct a join term.
    result = filtered_samples[0]
    for sample in filtered_samples[1:]:
        result = APP(APP(J, result), sample)
    return result


# FIXME The fair scheduler in _sample_nonlinear does not work yet; see (B2).
USE_FAIR_SCHEDULER = False


@logged(pretty, pretty, returns=pretty)
@memoize_args
def _app(lhs, rhs, nonlinear):
    head = lhs
    context = EMPTY_CONTEXT
    context = context_push(context, rhs)
    if nonlinear and USE_FAIR_SCHEDULER:
        samples = _sample_nonlinear(head, context)
    else:
        samples = _sample(head, context, nonlinear)
    return _join(samples, nonlinear)


@logged(pretty, returns=pretty)
@memoize_args
def _reduce(code, nonlinear):
    if is_app(code):
        return _app(code[1], code[2], nonlinear)
    elif is_quote(code):
        return QUOTE(_reduce(code[1], False))
    elif is_atom(code) or is_var(code):
        return code
    else:
        raise ValueError(code)


def reduce(code, budget=0):
    '''Beta-eta reduce code, ignoring budget.'''
    assert isinstance(budget, int) and budget >= 0, budget
    LOG.info('reduce({})'.format(pretty(code)))
    return _reduce(code, True)


def simplify(code):
    '''Linearly beta-eta reduce.'''
    LOG.info('simplify({})'.format(pretty(code)))
    return _reduce(code, False)
