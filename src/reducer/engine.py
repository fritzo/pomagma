'''Python reference implementation of beta-eta reduction engine.'''

from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args
from pomagma.reducer.code import I, K, B, C, S, BOT, TOP, APP, VAR
from pomagma.reducer.sugar import abstract
import itertools


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
def _app(lhs, rhs):
    avoid = free_vars(lhs) | free_vars(rhs)

    # Head reduce.
    head = lhs
    stack = [rhs]
    bound = []
    while not is_var(head):
        print('DEBUG head = {}'.format(head))
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
            stack.append(_app(y, z))
        elif head is C:
            x, y, z = pop(avoid, stack, bound, 3)
            head = x
            stack.append(y)
            stack.append(z)
        elif head is S:
            x, y, z = pop(avoid, stack, bound, 3)
            head = x
            stack.append(_app(y, z))
            stack.append(z)
        else:
            raise ValueError(head)

    # Reduce args.
    while stack:
        print('DEBUG head = {}'.format(head))
        arg = stack.pop()
        arg = _red(arg)
        head = APP(head, arg)

    # Abstract free variables.
    while bound:
        print('DEBUG head = {}'.format(head))
        var = bound.pop()
        head = abstract(var, head)

    print('DEBUG head = {}'.format(head))
    return head


def _red(code):
    return _app(code[1], code[2]) if is_app(code) else code


def reduce(code, budget=0):
    '''Beta-eta reduce code, ignoring budget.'''
    assert isinstance(budget, int) and budget >= 0, budget
    return _red(code)
