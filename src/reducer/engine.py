'''Python reference implementation of beta-eta reduction engine.'''

from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
from pomagma.reducer.code import I, K, B, C, S, BOT, TOP, APP, VAR
from pomagma.reducer.sugar import abstract
import itertools
import logging
import pomagma.util

# ----------------------------------------------------------------------------
# Logging

LOG_LEVELS = {
    pomagma.util.LOG_LEVEL_ERROR: logging.ERROR,
    pomagma.util.LOG_LEVEL_WARNING: logging.WARNING,
    pomagma.util.LOG_LEVEL_INFO: logging.INFO,
    pomagma.util.LOG_LEVEL_DEBUG: logging.DEBUG,
}

LOG = logging.getLogger(__name__)
LOG.setLevel(LOG_LEVELS[pomagma.util.LOG_LEVEL])
LOG.addHandler(logging.StreamHandler())


@memoize_args
def pretty(code, add_parens=False):
    if isinstance(code, str):
        return code
    elif code[0] == 'APP':
        lhs = pretty(code[1])
        rhs = pretty(code[2], True)
        return ('({} {})' if add_parens else '{} {}').format(lhs, rhs)
    elif code[0] == 'VAR':
        return code[1]
    else:
        raise NotImplementedError(code)


# ----------------------------------------------------------------------------
# Reduction

def is_var(code):
    return isinstance(code, tuple) and code[0] == 'VAR'


def is_app(code):
    return isinstance(code, tuple) and code[0] == 'APP'


@memoize_arg
def make_var(n):
    return VAR('v{}'.format(n))


@memoize_arg
def free_vars(code):
    if is_var(code):
        return set([code])
    elif is_app(code):
        return free_vars(code[1]) | free_vars(code[2])
    else:
        return set()


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
        arg = _red(arg)
        head = APP(head, arg)

    # Abstract free variables.
    while bound:
        LOG.debug('head = {}'.format(pretty(head)))
        var = bound.pop()
        head = abstract(var, head)

    LOG.debug('head = {}'.format(pretty(head)))
    return head


@memoize_arg
def _red(code):
    return _app(code[1], code[2], True) if is_app(code) else code


def reduce(code, budget=0):
    '''Beta-eta reduce code, ignoring budget.'''
    assert isinstance(budget, int) and budget >= 0, budget
    LOG.info('reduce({})'.format(pretty(code)))
    return _red(code)
