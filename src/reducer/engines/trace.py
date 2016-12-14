__all__ = [
    'trace_deterministic',
    'trace_nondeterministic',
    'lazy_print_trace',
]

from parsable import parsable
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import EVAL, QQUOTE, QAPP
from pomagma.reducer.code import NVAR, APP, QUOTE, FUN
from pomagma.reducer.code import is_nvar, is_app, is_join, is_quote, free_vars
from pomagma.reducer.code import sexpr_parse, sexpr_print
from pomagma.reducer.linker import link
from pomagma.reducer.transforms import abstract
import re

parsable = parsable.Parsable()

SUPPORTED_TESTDATA = ['sk', 'quote', 'lib']

# Tracer states.
REDUCE_HEAD = intern('REDUCE_HEAD')
REDUCE_ARGS = intern('REDUCE_ARGS')

# Stack operations.
APP_FUN = intern('APP_FUN')
APP_ARG = intern('APP_ARG')
ABS_VAR = intern('ABS_VAR')
QUOTE_ARG = intern('QUOTE_ARG')
EVAL_ARG = intern('EVAL_ARG')
QQUOTE_ARG = intern('QQUOTE_ARG')
QAPP_FUN = intern('QAPP_FUN')
QAPP_ARG = intern('QAPP_ARG')

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
    return NVAR('v{}'.format(next_id))


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


def trace_deterministic(code):
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
            elif is_nvar(code):
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
                stack = APP_ARG, APP(y, z), stack
                code = x
            elif code is C:
                x, stack = pop_arg(stack)
                y, stack = pop_arg(stack)
                z, stack = pop_arg(stack)
                stack = APP_ARG, y, stack
                stack = APP_ARG, z, stack
                code = x
            elif code is S:
                x, stack = pop_arg(stack)
                y, stack = pop_arg(stack)
                z, stack = pop_arg(stack)
                stack = APP_ARG, APP(y, z), stack
                stack = APP_ARG, z, stack
                code = x
            elif code is EVAL:
                x, stack = pop_arg(stack)
                stack = EVAL_ARG, None, stack
                code = x
            elif code is QQUOTE:
                x, stack = pop_arg(stack)
                stack = QQUOTE_ARG, None, stack
                code = x
            elif code is QAPP:
                x, stack = pop_arg(stack)
                y, stack = pop_arg(stack)
                stack = QAPP_ARG, y, stack
                code = x
            else:
                raise NotImplementedError(code)
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
            elif op is EVAL_ARG:
                if is_quote(code):
                    code = code[1]
                    state = REDUCE_HEAD
                elif code is TOP or code is BOT:
                    state = REDUCE_HEAD
                else:
                    code = APP(EVAL, code)
            elif op is QQUOTE_ARG:
                if is_quote(code):
                    code = QUOTE(code)
                elif code is TOP or code is BOT:
                    state = REDUCE_HEAD
                else:
                    code = APP(QQUOTE, code)
            elif op is QAPP_ARG:
                stack = QAPP_FUN, code, stack
                code = arg
                state = REDUCE_HEAD
            elif op is QAPP_FUN:
                lhs = arg
                rhs = code
                if lhs is TOP or rhs is TOP:
                    code = TOP
                    state = REDUCE_HEAD
                elif lhs is BOT or rhs is BOT:
                    code = BOT
                    state = REDUCE_HEAD
                elif is_quote(lhs) and is_quote(rhs):
                    code = QUOTE(APP(lhs[1], rhs[1]))
                    state = REDUCE_HEAD
                else:
                    code = APP(APP(QAPP, lhs), rhs)
            else:
                raise ValueError(op)
    return {'code': code, 'trace': trace}


def frame_eval(frame):
    state, code, stack = frame
    while stack is not None:
        op, arg, stack = stack
        if op is ABS_VAR:
            code = FUN(arg, code)
        elif op is APP_ARG:
            code = APP(code, arg)
        elif op is APP_FUN:
            code = APP(arg, code)
        elif op is QUOTE_ARG:
            code = QUOTE(code)
        else:
            raise ValueError(op)
    return code


class lazy_print_trace(object):
    __slots__ = ('_trace', '_message')

    def __init__(self, trace, message='Trace:'):
        self._trace = trace
        self._message = message

    def __str__(self):
        return '{}\n{}'.format(self._message, '\n'.join(
            '{} {}'.format(state, sexpr_print(code))
            for state, code, stack in self._trace
        ))

    def __repr__(self):
        return str(self)


# ----------------------------------------------------------------------------
# Scheduler as immutable stack = lifo queue (hence not complete)

def schedule_init():
    schedule = None
    return schedule


def schedule_is_empty(schedule):
    return schedule is None


def schedule_pop(schedule):
    task, schedule = schedule
    return schedule, task


def schedule_peek(schedule):
    task, schedule = schedule
    return task


def schedule_iter(schedule):
    while not schedule_is_empty(schedule):
        task, schedule = schedule_pop(schedule)
        yield task


def schedule_filter(schedule, pred):
    if schedule is None:
        return schedule
        task, tail = schedule
        filtered_tail = schedule_filter(tail, pred)
        if filtered_tail == tail:
            return schedule if pred(task) else tail
        else:
            tail = filtered_tail
            return schedule_push(tail, task) if pred(task) else tail


def try_decide_less(task_x, task_y):
    """Weak oracle deciding ordering between tasks-as-continuations."""
    if task_x[1] is BOT or task_y[1] is TOP or task_x == task_y:
        return True
    return None


def schedule_push(schedule, task):
    schedule = schedule_filter(
        schedule,
        lambda t: not try_decide_less(t, task),
    )
    if any(try_decide_less(task, t) for t in schedule_iter(schedule)):
        return schedule
    schedule = schedule_push(schedule, task)
    return schedule


def trace_nondeterministic(code):
    # FIXME This confuses the stack and schedule, and fails to recurse joins.
    init_fresh(code)
    state = REDUCE_HEAD
    stack = None
    task = state, code, stack
    schedule = schedule_init()
    schedule = schedule_push(schedule, task)
    trace = []
    result = set()
    while not schedule_is_empty(schedule):
        trace.append(schedule)
        schedule, task = schedule_pop(schedule)
        state, code, stack = task
        if state is REDUCE_HEAD:
            if is_app(code):
                stack = APP_ARG, code[2], stack
                code = code[1]
            elif is_join(code):
                task = state, code[2], stack
                schedule = schedule_push(schedule, task)
                code = code[1]
            elif is_quote(code):
                stack = QUOTE_ARG, None, stack
                code = code[1]
            elif is_nvar(code):
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
                stack = APP_ARG, APP(y, z), stack
                code = x
            elif code is C:
                x, stack = pop_arg(stack)
                y, stack = pop_arg(stack)
                z, stack = pop_arg(stack)
                stack = APP_ARG, y, stack
                stack = APP_ARG, z, stack
                code = x
            elif code is S:
                x, stack = pop_arg(stack)
                y, stack = pop_arg(stack)
                z, stack = pop_arg(stack)
                stack = APP_ARG, APP(y, z), stack
                stack = APP_ARG, z, stack
                code = x
            else:
                raise NotImplementedError(code)
        elif state is REDUCE_ARGS:
            if stack is None:
                result.add(code)
                continue
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
        task = state, code, stack
        schedule = schedule_push(schedule, task)
    return {'code': result, 'trace': trace}


@parsable
def trace_frames(sexpr, deterministic=True):
    """Print (state,code) pairs of a trace of reduction sequence."""
    code = sexpr_parse(sexpr)
    code = link(code)
    if deterministic:
        for state, code, stack in trace_deterministic(code)['trace']:
            print('{} {}'.format(state, sexpr_print(code)))
    else:
        for schedule in trace_nondeterministic(code)['trace']:
            for i, task in schedule_iter(schedule):
                state, code, stack = task
                prefix = '--' if i == 0 else '  '
                print('{} {} {}'.format(prefix, state, sexpr_print(code)))


@parsable
def trace_codes(sexpr):
    """Print evaluated code for each frame of a trace of reduction sequence."""
    code = sexpr_parse(sexpr)
    code = link(code)
    for frame in trace_deterministic(code)['trace']:
        code = frame_eval(frame)
        print(sexpr_print(code))


if __name__ == '__main__':
    parsable()
