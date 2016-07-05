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
    for i in itertools.count():
        var = make_var(i)
        if var not in avoid:
            return var


Context = namedtuple('Context', ['stack', 'bound', 'avoid'])


def context_make(avoid):
    assert isinstance(avoid, frozenset)
    return Context(None, None, avoid)


EMPTY_CONTEXT = context_make(frozenset())


def context_pop(context):
    if context.stack is not None:
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
    # Head reduce.
    while True:
        LOG.debug('head = {}'.format(pretty(head)))
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
            x = _reduce(x, nonlinear)
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
                yield head, old_context
                return
        elif head is J:
            x, context = context_pop(context)
            y, context = context_pop(context)
            for head in (x, y):
                for continuation in _sample(head, context, nonlinear):
                    yield continuation
        elif head is EVAL:
            x, context = context_pop(context)
            x = _reduce(x, nonlinear)
            if is_quote(x):
                head = x[1]
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
            y, context = context_pop(context)
            x = _reduce(x, nonlinear)
            y = _reduce(y, nonlinear)
            if is_quote(x) and is_quote(y):
                # FIXME This is too eager; see (B1).
                head = QUOTE(_app(x[1], y[1], nonlinear))
            else:
                head = APP(APP(QAPP, x), y)
                yield head, context
                return
        elif head in TRY_DECIDE:
            pred = head
            x, context = context_pop(context)
            y, context = context_pop(context)
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
            # FIXME This fails to err when it is unknown whether x or y errs.
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


def _close(continuation, nonlinear):
    """Close a continuation in linear-beta-eta normal form."""
    head, context = continuation
    PROFILE_COUNTERS[_close, head[0] if isinstance(head, tuple) else head] += 1

    # Reduce args.
    for arg in iter_shared_list(context.stack):
        LOG.debug('head = {}'.format(pretty(head)))
        arg = _reduce(arg, nonlinear)
        head = APP(head, arg)

    # Abstract free variables.
    for var in iter_shared_list(context.bound):
        LOG.debug('head = {}'.format(pretty(head)))
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
    if not samples:
        return BOT

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


@logged(pretty, pretty, returns=pretty)
@memoize_args
def _app(lhs, rhs, nonlinear):
    head = lhs
    context = context_make(free_vars(lhs) | free_vars(rhs))
    context = context_push(context, rhs)
    return _join(_sample(head, context, nonlinear), nonlinear)


@logged(pretty, returns=pretty)
@memoize_args
def _reduce(code, nonlinear):
    if is_app(code):
        return _app(code[1], code[2], nonlinear)
    elif is_quote(code):
        return QUOTE(_reduce(code[1], nonlinear))
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
    return _reduce(code, False)


def sample(code, budget=0):
    assert isinstance(budget, int) and budget >= 0, budget
    '''Beta-eta sample code, ignoring budget.'''
    head = code
    context = context_make(free_vars(code))
    for continuation in _sample(head, context, nonlinear=True):
        yield _close(continuation, nonlinear=True)
