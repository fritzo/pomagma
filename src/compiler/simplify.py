from pomagma.compiler.expressions import Expression
from pomagma.compiler.expressions import Expression_0
from pomagma.compiler.expressions import Expression_2
from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args

TOP = Expression_0('TOP')
BOT = Expression_0('BOT')
I = Expression_0('I')
F = Expression_0('F')
K = Expression_0('K')
B = Expression_0('B')
C = Expression_0('C')
J = Expression_0('J')
CB = Expression_0('CB')
CI = Expression_0('CI')
APP = Expression_2('APP')
COMP = Expression_2('COMP')
JOIN = Expression_2('JOIN')


@memoize_args
def simplify_stack(head, *args):
    nargs = len(args)
    if head == TOP:
        return [TOP]
    elif head == BOT:
        return [BOT]
    elif head == I:
        if nargs >= 1:
            return simplify_stack(*args)
    elif head == F:
        if nargs >= 1:
            return simplify_stack(I, *args[1:])
    elif head == K:
        if nargs >= 2:
            return simplify_stack(args[0], *args[2:])
    elif head == B:
        if nargs >= 3:
            return simplify_stack(args[0], APP(args[1], args[2]), *args[3:])
    elif head == C:
        if nargs >= 3:
            return simplify_stack(args[0], args[2], args[1], *args[3:])
    elif head == J:
        if nargs >= 2:
            return simplify_stack(JOIN(args[0], args[1]), *args[2:])
    elif head == CB:
        return simplify_stack(C, B, *args)
    elif head == CI:
        return simplify_stack(C, I, *args)
    elif head.name == 'APP':
        lhs, rhs = head.args
        return simplify_stack(lhs, rhs, *args)
    elif head.name == 'COMP':
        if nargs >= 1:
            lhs, rhs = head.args
            return simplify_stack(lhs, APP(rhs, args[0]), *args[1:])
    elif head.name == 'JOIN':
        lhs, rhs = map(simplify, head.args)
        if lhs == TOP or rhs == TOP:
            return [TOP]
        elif lhs == BOT:
            return simplify_stack(rhs, *args)
        elif rhs == BOT:
            return simplify_stack(lhs, *args)
        elif lhs == rhs:
            # idempotence
            return simplify_stack(lhs, *args)
        else:
            # commutativity
            lhs, rhs = sorted((lhs, rhs))
            return [JOIN(lhs, rhs)] + map(simplify, args)
        # TODO simplify wrt associativity

    head = Expression.make(head.name, *map(simplify, head.args))
    return [head] + map(simplify, args)


@memoize_arg
def simplify(term):
    stack = simplify_stack(term)
    term = stack[0]
    for arg in stack[1:]:
        term = APP(term, arg)
    return term
