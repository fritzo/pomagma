'''Python reference implementation of beta-eta reduction engine.

Environment Variables:
    POMAGMA_PROFILE_ENGINE

Known Bugs:
(B1) Evaluation is too eager wrt quoting. Eg the engine should not reduce
    lib.list_map eagerly unless it has an argument, but
    qapp(quote(list_map), quote(I), quote(nil)) will evaluate list_map too
    soon.
    OK: reduce(app(list_map, I, nil))
    DIV: reduce(app(list_map, I))
    DIV: reduce(qapp(quote(list_map), quote(I), quote(nil)))
'''

__all__ = ['reduce', 'simplify', 'sample']

from collections import namedtuple
from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
from pomagma.reducer import oracle
from pomagma.reducer.code import EVAL, QQUOTE, QAPP, EQUAL, LESS
from pomagma.reducer.code import HOLE, TOP, BOT, I, K, B, C, S, J
from pomagma.reducer.code import UNIT, BOOL, MAYBE
from pomagma.reducer.code import VAR, APP, QUOTE
from pomagma.reducer.code import is_var, is_app, is_quote, free_vars
from pomagma.reducer.sugar import abstract
from pomagma.reducer.util import LOG
from pomagma.reducer.util import PROFILE_COUNTERS
from pomagma.reducer.util import logged
from pomagma.reducer.util import pretty
import itertools

true = K
false = APP(K, I)


# ----------------------------------------------------------------------------
# Immutable shared contexts

@memoize_arg
def make_var(n):
    return VAR('v{}'.format(n))


def fresh(avoid):
    """Return the smallest variable not in avoid."""
    PROFILE_COUNTERS[fresh, len(avoid)] += 1
    var = 0
    for var in itertools.imap(make_var, itertools.count()):
        if var not in avoid:
            return var


Context = namedtuple('Context', ['stack', 'bound', 'avoid'])


def context_make(avoid):
    return Context(None, None, frozenset(avoid))


def context_pop(context):
    if context.stack:
        arg, stack = context.stack
        return arg, Context(stack, context.bound, context.avoid)
    else:
        arg = fresh(context.avoid)
        avoid = context.avoid | frozenset([arg])
        bound = arg, context.bound
        return arg, Context(context.stack, bound, avoid)


def context_push(context, arg):
    stack = arg, context.stack
    return Context(stack, context.bound, context.avoid)


def iter_shared_list(shared_list):
    while shared_list is not None:
        arg, shared_list = shared_list
        yield arg


# ----------------------------------------------------------------------------
# Reduction

def _close(head, context, nonlinear):
    PROFILE_COUNTERS[_close, head[0] if isinstance(head, tuple) else head] += 1
    # Reduce args.
    for arg in iter_shared_list(context.stack):
        LOG.debug('head = {}'.format(pretty(head)))
        arg = _red(arg, nonlinear)
        head = APP(head, arg)

    # Abstract free variables.
    for var in iter_shared_list(context.bound):
        LOG.debug('head = {}'.format(pretty(head)))
        head = abstract(var, head)

    return head


def try_unquote(code):
    return code[1] if is_quote(code) else None


TRY_CAST = {
    BOOL: oracle.try_cast_bool,
    UNIT: oracle.try_cast_unit,
    MAYBE: oracle.try_cast_maybe,
}


def _sample(head, context, nonlinear):
    # Head reduce.
    while True:
        LOG.debug('head = {}'.format(pretty(head)))
        PROFILE_COUNTERS[
            _sample, head[0] if isinstance(head, tuple) else head] += 1
        if is_app(head):
            context = context_push(context, head[2])
            head = head[1]
        elif is_var(head):
            yield _close(head, context, nonlinear)
            return
        elif is_quote(head):
            x = head[1]
            x = _red(x, nonlinear)
            head = QUOTE(x)
            yield _close(head, context, nonlinear)
            return
        elif head is HOLE:
            yield HOLE
            return
        elif head is TOP:
            yield TOP
            return
        elif head is BOT:
            return
        elif head is I:
            head, context = context_pop(context)
        elif head is K:
            x, context = context_pop(context)
            y, context = context_pop(context)
            head = x
        elif head is B:
            x, context = context_pop(context)
            y, context = context_pop(context)
            z, context = context_pop(context)
            head = x
            context = context_push(context, _app(y, z, False))
        elif head is C:
            x, context = context_pop(context)
            y, context = context_pop(context)
            z, context = context_pop(context)
            head = x
            context = context_push(context, y)
            context = context_push(context, z)
        elif head is S:
            old_context = context
            x, context = context_pop(context)
            y, context = context_pop(context)
            z, context = context_pop(context)
            if nonlinear or is_var(z):
                head = x
                context = context_push(context, _app(y, z, False))
                context = context_push(context, z)
            else:
                yield _close(head, old_context, nonlinear)
                return
        elif head is J:
            x, context = context_pop(context)
            y, context = context_pop(context)
            for head in (x, y):
                for term in _sample(head, context, nonlinear):
                    yield term
        elif head is EVAL:
            x, context = context_pop(context)
            x = _red(x, nonlinear)
            if is_quote(x):
                head = x[1]
            else:
                head = APP(EVAL, x)
                yield _close(head, context, nonlinear)
                return
        elif head is QQUOTE:
            x, context = context_pop(context)
            x = _red(x, nonlinear)
            if x is TOP:
                yield TOP
                return
            elif x is BOT:
                return
            elif is_quote(x):
                head = QUOTE(x)
            else:
                head = APP(QQUOTE, x)
                yield _close(head, context, nonlinear)
                return
        elif head is QAPP:
            x, context = context_pop(context)
            y, context = context_pop(context)
            x = _red(x, nonlinear)
            y = _red(y, nonlinear)
            if is_quote(x) and is_quote(y):
                # FIXME This is too eager; see (B1).
                head = QUOTE(_app(x[1], y[1], nonlinear))
            else:
                head = APP(APP(QAPP, x), y)
                yield _close(head, context, nonlinear)
                return
        elif head is EQUAL:
            x, context = context_pop(context)
            y, context = context_pop(context)
            x = _red(x, nonlinear)
            y = _red(y, nonlinear)
            if x is TOP or y is TOP:
                yield TOP
                return
            elif (x is BOT and is_quote(y)) or (is_quote(x) and y is BOT):
                return
            answer = oracle.try_decide_equal(try_unquote(x), try_unquote(y))
            if answer is True:
                head = true
            elif answer is False:
                head = false
            else:
                assert answer is None
                head = APP(APP(EQUAL, x), y)
                yield _close(head, context, nonlinear)
                return
        elif head is LESS:
            x, context = context_pop(context)
            y, context = context_pop(context)
            x = _red(x, nonlinear)
            y = _red(y, nonlinear)
            if x is TOP or y is TOP:
                yield TOP
                return
            answer = oracle.try_decide_less(try_unquote(x), try_unquote(y))
            if answer is True:
                head = true
            elif answer is False:
                head = false
            else:
                assert answer is None
                head = APP(APP(LESS, x), y)
                yield _close(head, context, nonlinear)
                return
        elif head in TRY_CAST:
            type_ = head
            x, context = context_pop(context)
            x = _red(x, nonlinear)
            while is_app(x) and x[1] is type_:
                x = x[2]
            head = TRY_CAST[type_](x)
            if head is None:
                head = APP(type_, x)
                yield _close(head, context, nonlinear)
                return
        else:
            raise ValueError(head)


def _collect(samples):
    PROFILE_COUNTERS[_collect, '...'] += 1
    unique_samples = set()
    for sample in samples:
        if sample is TOP:
            return TOP
        unique_samples.add(sample)
    if not unique_samples:
        return BOT
    if len(unique_samples) == 1:
        return unique_samples.pop()
    filtered_samples = sorted([
        sample
        for sample in unique_samples
        if not any(oracle.try_decide_less(sample, other)
                   for other in unique_samples
                   if other is not sample)
    ])
    result = filtered_samples[0]
    for sample in filtered_samples[1:]:
        result = APP(APP(J, result), sample)
    return result


@logged(pretty, pretty, returns=pretty)
@memoize_args
def _app(lhs, rhs, nonlinear):
    context = context_make(free_vars(lhs) | free_vars(rhs))
    head = lhs
    context = context_push(context, rhs)
    return _collect(_sample(head, context, nonlinear))


@logged(pretty, returns=pretty)
@memoize_args
def _red(code, nonlinear):
    if is_app(code):
        return _app(code[1], code[2], nonlinear)
    elif is_quote(code):
        return QUOTE(_red(code[1], nonlinear))
    else:
        return code


def reduce(code, budget=0):
    '''Beta-eta reduce code, ignoring budget.'''
    assert isinstance(budget, int) and budget >= 0, budget
    LOG.info('reduce({})'.format(pretty(code)))
    return _red(code, True)


def simplify(code):
    '''Linearly beta-eta reduce.'''
    return _red(code, False)


def sample(code, budget=0):
    assert isinstance(budget, int) and budget >= 0, budget
    '''Beta-eta sample code, ignoring budget.'''
    context = context_make(free_vars(code))
    return _sample(code, context, True)
