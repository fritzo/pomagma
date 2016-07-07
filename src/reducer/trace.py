__all__ = ['trace_reduce']

from parsable import parsable
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S, J, VAR, APP, QUOTE
from pomagma.reducer.code import is_var, is_app, is_quote, free_vars
from pomagma.reducer.code import sexpr_parse, sexpr_print
from pomagma.reducer.transforms import abstract
from pomagma.util import TODO
import re

parsable = parsable.Parsable()

# Tracer states.
REDUCE_HEAD = intern('REDUCE_HEAD')
REDUCE_ARGS = intern('REDUCE_ARGS')

# Stack operations.
APP_FUN = intern('APP_FUN')
APP_ARG = intern('APP_ARG')
ABS_VAR = intern('ABS_VAR')
QUOTE_ARG = intern('QUOTE_ARG')

re_var = re.compile(r'^v\d+$')
assert re_var.match('v0')
assert re_var.match('v1')
assert re_var.match('v234')
assert not re_var.match('x')


FRESH_ID = [None]


def init_fresh(code):
    ids = [int(var[1][1:]) for var in free_vars(code) if re_var.match(var[1])]
    FRESH_ID[0] = 1 + max(ids) if ids else 0


def fresh():
    next_id = FRESH_ID[0]
    FRESH_ID[0] += 1
    return VAR('v{}'.format(next_id))


def pop_arg(stack):
    if stack is not None and stack[0] is APP_ARG:
        arg = stack[1]
        stack = stack[2]
    else:
        arg = fresh()
        stack = ABS_VAR, arg, stack
    return arg, stack


def drop_args(stack):
    while stack is not None and stack[0] in (APP_ARG, ABS_VAR):
        stack = stack[2]
    return stack


def trace_reduce(code):
    init_fresh(code)
    state = REDUCE_HEAD
    stack = None
    trace = []
    while True:
        trace.append((state, code, stack))
        if state is REDUCE_HEAD:
            if is_app(code):
                stack = APP_ARG, code[2], stack
                code = code[1]
            elif is_quote(code):
                stack = QUOTE_ARG, None, stack
                code = code[1]
            elif is_var(code):
                state = REDUCE_ARGS
            elif code is TOP or code is BOT:
                stack = drop_args(stack)
                state = REDUCE_ARGS
            elif code is I:
                x, stack = pop_arg(stack)
                code = x
            elif code is K:
                x, stack = pop_arg(stack)
                y, stack = pop_arg(stack)
                code = x
            elif code is B:
                x, stack = pop_arg(stack)
                y, stack = pop_arg(stack)
                z, stack = pop_arg(stack)
                code = APP(x, APP(y, z))
            elif code is C:
                x, stack = pop_arg(stack)
                y, stack = pop_arg(stack)
                z, stack = pop_arg(stack)
                code = APP(APP(x, z), y)
            elif code is S:
                x, stack = pop_arg(stack)
                y, stack = pop_arg(stack)
                z, stack = pop_arg(stack)
                code = APP(APP(x, z), APP(y, z))
            elif code is J:
                TODO()
            else:
                raise ValueError(code)
        elif state is REDUCE_ARGS:
            if stack is None:
                break
            op, arg, stack = stack
            if op is ABS_VAR:
                code = abstract(arg, code)
            elif op is APP_ARG:
                fun = code
                code = arg
                stack = APP_FUN, fun, stack
                state = REDUCE_HEAD
            elif op is APP_FUN:
                code = APP(arg, code)
            elif op is QUOTE_ARG:
                code = QUOTE(code)
            else:
                raise ValueError(op)
    trace.append((state, code, stack))
    return trace


@parsable
def trace_codes(sexpr):
    """Print (state,code) pairs of a trace of reduction sequence."""
    code = sexpr_parse(sexpr)
    trace = trace_reduce(code)
    for state, code, stack in trace:
        print '{} {}'.format(state, sexpr_print(code))


if __name__ == '__main__':
    parsable()
