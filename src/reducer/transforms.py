'''Code-to-code transforms'''

from pomagma.compiler.util import memoize_args
from pomagma.reducer import pattern
from pomagma.reducer.code import HOLE, TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import VAR, APP, JOIN, FUN, LET
from pomagma.reducer.code import is_app
from pomagma.util import TODO


# ----------------------------------------------------------------------------
# Abstraction

_lhs = pattern.variable('lhs')
_rhs = pattern.variable('rhs')
_app_pattern = APP(_lhs, _rhs)
_join_pattern = JOIN(_lhs, _rhs)


@memoize_args
def try_abstract(var, body):
    """Returns \\var.body if var occurs in body, else None."""
    if body is var:
        return I  # Rule I.
    match = {}
    if pattern.matches(_app_pattern, body, match):
        lhs_abs = try_abstract(var, match[_lhs])
        rhs_abs = try_abstract(var, match[_rhs])
        if lhs_abs is None:
            if rhs_abs is None:
                return None  # Rule K.
            elif rhs_abs is I:
                return match[_lhs]  # Rule eta.
            else:
                return APP(APP(B, match[_lhs]), rhs_abs)  # Rule B.
        else:
            if rhs_abs is None:
                return APP(APP(C, lhs_abs), match[_rhs])  # Rule C.
            else:
                return APP(APP(S, lhs_abs), rhs_abs)  # Rule S.
    if pattern.matches(_join_pattern, body, match):
        lhs_abs = try_abstract(var, match[_lhs])
        rhs_abs = try_abstract(var, match[_rhs])
        if lhs_abs is None:
            if rhs_abs is None:
                return None  # Rule K.
            else:
                return JOIN(APP(K, match[_lhs]), rhs_abs)  # Rule JOIN.
        else:
            if rhs_abs is None:
                return JOIN(lhs_abs, APP(K, match[_rhs]))  # Rule JOIN.
            else:
                return JOIN(lhs_abs, rhs_abs)  # Rule JOIN.
    return None  # Rule K.


def abstract(var, body):
    result = try_abstract(var, body)
    return APP(K, body) if result is None else result


# ----------------------------------------------------------------------------
# Symbolic decompiler
# Adapted from pomagma/puddle-syntax/lib/compiler.js decompile()

def fresh():
    TODO('find a fresh variable')
    return VAR('x')


def _to_stack(code):
    head = code
    args = None
    while is_app(code):
        args = (code[2], args)
        head = code[1]
    return head, args


def _from_stack(stack):
    head, args = stack
    while args is not None:
        arg, args = args
        head = APP(head, arg)
    return head


def _decompile_args_untyped(args):
    if args is None:
        return None
    arg, args = args
    arg = decompile_untyped(arg)
    args = _decompile_args_untyped(args)
    return (arg, args)


_x = pattern.variable('x')
_y = pattern.variable('y')
_z = pattern.variable('z')
_args = pattern.variable('args')
_name = pattern.variable('name')


def _decompile_stack_untyped(stack):
    match = {}
    if stack is None:
        return None
    if pattern.matches((HOLE, _args), stack, match):
        stack = (HOLE, _decompile_args_untyped(match[_args]))
        return _from_stack(stack)
    if pattern.matches((TOP, _args), stack, match):
        return TOP
    if pattern.matches((BOT, _args), stack, match):
        return BOT
    if pattern.matches((I, None), stack):
        x = fresh()
        return FUN(x, x)
    if pattern.matches((I, _args), stack, match):
        return _decompile_stack_untyped(match[_args])
    if pattern.matches((K, None), stack, match):
        x = fresh()
        y = fresh()
        return FUN(x, FUN(y, x))
    if pattern.matches((K, (_x, _args)), stack, match):
        x = match[_x]
        y = fresh()
        return FUN(y, x)
    if pattern.matches((K, (_x, (_y, _args))), stack, match):
        x = match[_x]
        args = match[_args]
        return _decompile_stack_untyped((x, args))
    if pattern.match((B, None), stack, match):
        x = fresh()
        y = fresh()
        z = fresh()
        return FUN(x, FUN(y, FUN(z, APP(x, APP(y, z)))))
    if pattern.match((B, (_x, None)), stack, match):
        y = fresh()
        z = fresh()
        xyz = _decompile_stack_untyped(_to_stack(match[_x], APP(y, z), None))
        return FUN(y, FUN(z, xyz))
    if pattern.match((B, (_x, (_y, None))), stack, match):
        z = fresh()
        xyz = _decompile_stack_untyped(
            _to_stack(match[_x], APP(match[_y], z), None))
        return FUN(z, xyz)
    if pattern.match((B, (_x, (_y, (_z, _args)))), stack, match):
        return _decompile_stack_untyped(
            _to_stack(match[_x], APP(match[_y], match[_z]), match[_args]))
    if pattern.match(C, None, stack, match):
        x = fresh()
        y = fresh()
        z = fresh()
        return FUN(x, FUN(y, FUN(z, APP(APP(x, z), y))))
    if pattern.match((C, (_x, None)), stack, match):
        y = fresh()
        z = fresh()
        xzy = _decompile_stack_untyped(_to_stack(match[_x], z, y, None))
        return FUN(y, FUN(z, xzy))
    if pattern.match((C, (_x, (_y, None))), stack, match):
        z = fresh()
        xzy = _decompile_stack_untyped(
            _to_stack(match[_x], z, match[_y], None))
        return FUN(z, xzy)
    if pattern.match((C, (_x, (_y, (_z, _args)))), stack, match):
        return _decompile_stack_untyped(
            _to_stack(match[_x], match[_z], match[_y], match[_args]))
    if pattern.match((S, None), stack, match):
        x = fresh()
        y = fresh()
        z = fresh()
        return FUN(x, FUN(y, FUN(z, APP(APP(x, z), APP(y, z)))))
    if pattern.match((S, (_x, None)), stack, match):
        y = fresh()
        z = fresh()
        tx = decompile_untyped(match[_x])
        return FUN(y, FUN(z, APP(APP(tx, z), APP(y, z))))
    if pattern.match((S, (_x, (_y, None))), stack, match):
        z = fresh()
        tx = decompile_untyped(match[_x])
        ty = decompile_untyped(match[_y])
        return FUN(z, APP(APP(tx, z), APP(ty, z)))
    if pattern.match((S, (_x, (_y, (VAR(_name), _args)))), stack, match):
        z = VAR(match[_name])
        head = decompile_untyped(APP(APP(match[_x], z), APP(match[_y], z)))
        args = _decompile_args_untyped(match[_args])
        return _from_stack(stack(head, args))
    if pattern.match((S, (_x, (_y, (_z, _args)))), stack, match):
        z = fresh()
        tz = decompile_untyped(match[_z])
        xz = APP(match[_x], z)
        yz = APP(match[_y], z)
        head = LET(z, tz, decompile(APP(xz, yz)))
        args = _decompile_args_untyped(match[_args])
        return _from_stack(stack(head, args))
    TODO('match other cases')


def decompile_untyped(code):
    stack = _to_stack(code)
    return _decompile_stack_untyped(stack)


def decompile(code, schema=None):
    if schema is None:
        return decompile_untyped(code)
    else:
        TODO('implement schema-annotated decompilation')
