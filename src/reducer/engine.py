'''Python reference implementation of beta-eta reduction engine.'''

from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
from pomagma.reducer.code import I, K, B, C, S, BOT, TOP, APP, JOIN, VAR
from pomagma.reducer.code import is_var, is_app, is_join, free_vars
from pomagma.reducer.sugar import abstract
from pomagma.reducer.util import LOG
from pomagma.reducer.util import logged
from pomagma.reducer.util import pretty
import itertools
from collections import namedtuple


# ----------------------------------------------------------------------------
# Immutable shared contexts

@memoize_arg
def make_var(n):
    return VAR('v{}'.format(n))


def fresh(avoid):
    """Return the smallest variable not in avoid."""
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

@logged(pretty, pretty, returns=pretty)
@memoize_args
def _app(lhs, rhs, nonlinear):
    context = context_make(free_vars(lhs) | free_vars(rhs))

    # Head reduce.
    head = lhs
    context = context_push(context, rhs)
    while not is_var(head):
        LOG.debug('head = {}'.format(pretty(head)))
        if is_app(head):
            context = context_push(context, head[2])
            head = head[1]
        elif is_join(head):
            raise NotImplementedError('TODO implement sampling')
        elif head is TOP:
            return TOP
        elif head is BOT:
            return BOT
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
                context = old_context
                break
        else:
            raise ValueError(head)

    # Reduce args.
    for arg in iter_shared_list(context.stack):
        LOG.debug('head = {}'.format(pretty(head)))
        arg = _red(arg, nonlinear)
        head = APP(head, arg)

    # Abstract free variables.
    for var in iter_shared_list(context.bound):
        LOG.debug('head = {}'.format(pretty(head)))
        head = abstract(var, head)

    # LOG.debug('head = {}'.format(pretty(head)))
    return head


def add_samples(code, sample_set):
    if code is TOP:
        sample_set.clear()
        sample_set.add(TOP)
    elif code is BOT:
        return
    elif is_join(code):
        add_samples(code[1], sample_set)
        add_samples(code[2], sample_set)
    else:
        sample_set.add(code)


@logged(pretty, pretty, returns=pretty)
@memoize_args
def _join(lhs, rhs, nonlinear):
    lhs = _red(lhs, nonlinear)
    rhs = _red(rhs, nonlinear)
    sample_set = set()
    add_samples(lhs, sample_set)
    add_samples(rhs, sample_set)
    if not sample_set:
        return BOT
    if TOP in sample_set:
        return TOP
    samples = sorted(sample_set)
    result = samples[0]
    for part in samples[1:]:
        result = JOIN(result, part)
    return result


@logged(pretty, returns=pretty)
@memoize_args
def _red(code, nonlinear):
    if is_app(code):
        return _app(code[1], code[2], nonlinear)
    elif is_join(code):
        return _join(code[1], code[2], nonlinear)
    else:
        return code


def reduce(code, budget=0):
    '''Beta-eta reduce code, ignoring budget.'''
    assert isinstance(budget, int) and budget >= 0, budget
    LOG.info('reduce({})'.format(pretty(code)))
    return _red(code, True)


def simplify(code):
    return _red(code, False)
