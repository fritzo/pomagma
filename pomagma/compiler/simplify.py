from pomagma.compiler.expressions import Expression, Expression_0, Expression_2
from pomagma.compiler.util import memoize_arg, memoize_args

TOP = Expression_0("TOP")
BOT = Expression_0("BOT")
I = Expression_0("I")
F = Expression_0("F")
K = Expression_0("K")
B = Expression_0("B")
C = Expression_0("C")
J = Expression_0("J")
CB = Expression_0("CB")
CI = Expression_0("CI")
HOLE = Expression_0("HOLE")
APP = Expression_2("APP")
COMP = Expression_2("COMP")
JOIN = Expression_2("JOIN")

is_terminal = (TOP, BOT, HOLE).__contains__


@memoize_args
def simplify_stack(head, *args):
    args = list(map(simplify_term, args))
    nargs = len(args)
    if is_terminal(head):
        return [head]
    if head == I:
        if nargs >= 1:
            return simplify_stack(*args)
    elif head == F:
        if nargs >= 1:
            return simplify_stack(I, *args[1:])
    elif head == K:
        if nargs >= 1 and is_terminal(args[0]):
            return [args[0]]
        if nargs >= 2:
            return simplify_stack(args[0], *args[2:])
    elif head == B:
        if nargs >= 1 and is_terminal(args[0]):
            return [args[0]]
        if nargs >= 3:
            return simplify_stack(args[0], APP(args[1], args[2]), *args[3:])
    elif head == C:
        if nargs >= 1 and is_terminal(args[0]):
            return [args[0]]
        if nargs >= 3:
            return simplify_stack(args[0], args[2], args[1], *args[3:])
    elif head == J:
        if nargs >= 2:
            return simplify_stack(JOIN(args[0], args[1]), *args[2:])
    elif head == CB:
        return simplify_stack(C, B, *args)
    elif head == CI:
        return simplify_stack(C, I, *args)
    elif head.name == "APP":
        lhs, rhs = head.args
        return simplify_stack(lhs, rhs, *args)
    elif head.name == "COMP":
        lhs, rhs = list(map(simplify_term, head.args))
        if is_terminal(lhs):
            return [lhs]
        if lhs == I:
            return simplify_stack(rhs, *args)
        if rhs == I:
            return simplify_stack(lhs, *args)
        if nargs >= 1:
            return simplify_stack(lhs, APP(rhs, args[0]), *args[1:])
    elif head.name == "JOIN":
        lhs, rhs = list(map(simplify_term, head.args))
        if lhs == TOP or rhs == TOP:
            return [TOP]
        if lhs == BOT:
            return simplify_stack(rhs, *args)
        if rhs == BOT:
            return simplify_stack(lhs, *args)
        if lhs == rhs:
            # idempotence
            return simplify_stack(lhs, *args)
        # commutativity
        lhs, rhs = sorted((lhs, rhs))
        return [JOIN(lhs, rhs), *args]
        # TODO simplify wrt associativity

    head = Expression(head.name, *list(map(simplify_term, head.args)))
    return [head, *args]


@memoize_arg
def simplify_term(term):
    stack = simplify_stack(term)
    term = stack[0]
    for arg in stack[1:]:
        term = APP(term, arg)
    return term


@memoize_arg
def simplify_expr(expr):
    if expr.is_rel():
        args = list(map(simplify_term, expr.args))
        return Expression(expr.name, *args)
    return simplify_term(expr)
