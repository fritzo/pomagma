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


@memoize_arg
def make_var(n):
    return VAR('v{}'.format(n))


def fresh(avoid):
    """Return the smallest variable not in avoid."""
    var = 0
    for var in itertools.imap(make_var, itertools.count()):
        if var not in avoid:
            return var


def pop(avoid, stack, bound, count):
    result = []
    for _ in xrange(count):
        try:
            result.append(stack.pop())
        except IndexError:
            var = fresh(avoid)
            avoid.add(var)
            bound.append(var)
            result.append(var)
    return result


@logged(pretty, pretty, returns=pretty)
@memoize_args
def _app(lhs, rhs, nonlinear):
    avoid = free_vars(lhs) | free_vars(rhs)

    # Head reduce.
    head = lhs
    stack = [rhs]
    bound = []
    while not is_var(head):
        LOG.debug('head = {}'.format(pretty(head)))
        if is_app(head):
            stack.append(head[2])
            head = head[1]
        elif is_join(head):
            raise NotImplementedError('TODO implement sampling')
        elif head is TOP:
            return TOP
        elif head is BOT:
            return BOT
        elif head is I:
            head, = pop(avoid, stack, bound, 1)
        elif head is K:
            x, y = pop(avoid, stack, bound, 2)
            head = x
        elif head is B:
            x, y, z = pop(avoid, stack, bound, 3)
            head = x
            stack.append(_app(y, z, False))
        elif head is C:
            x, y, z = pop(avoid, stack, bound, 3)
            head = x
            stack.append(y)
            stack.append(z)
        elif head is S:
            x, y, z = pop(avoid, stack, bound, 3)
            if nonlinear or is_var(z):
                head = x
                stack.append(_app(y, z, False))
                stack.append(z)
            else:
                break
        else:
            raise ValueError(head)

    # Reduce args.
    while stack:
        LOG.debug('head = {}'.format(pretty(head)))
        arg = stack.pop()
        arg = _red(arg, nonlinear)
        head = APP(head, arg)

    # Abstract free variables.
    while bound:
        LOG.debug('head = {}'.format(pretty(head)))
        var = bound.pop()
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
