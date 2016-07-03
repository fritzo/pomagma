'''Code-to-code transforms.'''

__all__ = ['try_abstract', 'abstract', 'decompile']

from pomagma.compiler.util import memoize_args
from pomagma.reducer import pattern
from pomagma.reducer.code import HOLE, TOP, BOT, I, K, B, C, S, J
from pomagma.reducer.code import VAR, APP, FUN, LET
from pomagma.reducer.code import is_var, is_app, is_fun, is_let


# ----------------------------------------------------------------------------
# Abstraction

@memoize_args
def try_abstract(var, body):
    """Returns \\var.body if var occurs in body, else None."""
    if not is_var(var):
        raise NotImplementedError('Only variables can be abstracted')
    if body is var:
        return I  # Rule I
    elif is_app(body):
        if is_app(body[1]) and body[1][1] is J:
            lhs = body[1][2]
            rhs = body[2]
            lhs_abs = try_abstract(var, lhs)
            rhs_abs = try_abstract(var, rhs)
            if lhs_abs is None:
                if rhs_abs is None:
                    return None  # Rule K
                elif rhs_abs is I:
                    return APP(J, lhs)  # Rule J-eta
                else:
                    return APP(APP(B, APP(J, lhs)), rhs_abs)  # Rule J-B
            else:
                if rhs_abs is None:
                    if lhs_abs is I:
                        return APP(J, rhs)  # Rule J-eta
                    else:
                        return APP(APP(B, APP(J, rhs)), lhs_abs)  # Rule J-B
                else:
                    return APP(APP(J, lhs_abs), rhs_abs)  # Rule J
        else:
            lhs = body[1]
            rhs = body[2]
            lhs_abs = try_abstract(var, lhs)
            rhs_abs = try_abstract(var, rhs)
            if lhs_abs is None:
                if rhs_abs is None:
                    return None  # Rule K
                elif rhs_abs is I:
                    return lhs  # Rule eta
                else:
                    return APP(APP(B, lhs), rhs_abs)  # Rule B
            else:
                if rhs_abs is None:
                    return APP(APP(C, lhs_abs), rhs)  # Rule C
                else:
                    return APP(APP(S, lhs_abs), rhs_abs)  # Rule S
    else:
        return None  # Rule K


def abstract(var, body):
    result = try_abstract(var, body)
    return APP(K, body) if result is None else result


# ----------------------------------------------------------------------------
# Symbolic compiler : FUN,LET -> I,K,B,C,S

def compile_(code):
    if isinstance(code, str):
        return code
    elif is_var(code):
        return code
    elif is_app(code):
        x = compile_(code[1])
        y = compile_(code[2])
        return APP(x, y)
    elif is_fun(code):
        var = code[1]
        body = compile_(code[2])
        return abstract(var, body)
    elif is_let(code):
        var = code[1]
        defn = compile_(code[2])
        body = compile_(code[3])
        return APP(abstract(var, body), defn)
    else:
        raise ValueError('Cannot compile_: {}'.format(code))


# ----------------------------------------------------------------------------
# Symbolic decompiler : I,K,B,C,S -> FUN,LET

FRESH_ID = 0
FRESH_VARS = map(VAR, 'abcdefghijklmnopqrstuvwxyz')
fresh_var = FRESH_VARS.__getitem__


def _fresh():
    global FRESH_ID
    result = fresh_var(FRESH_ID)
    FRESH_ID += 1
    return result


def _to_stack(head, *args_tuple):
    args = args_tuple[-1]
    for arg in reversed(args_tuple[:-1]):
        args = (arg, args)
    while is_app(head):
        args = (head[2], args)
        head = head[1]
    return head, args


def _from_stack(stack):
    head, args = stack
    while args is not None:
        arg, args = args
        head = APP(head, arg)
    return head


def _decompile_args(args):
    if args is None:
        return None
    arg, args = args
    arg = _decompile(arg)
    args = _decompile_args(args)
    return (arg, args)


_x = pattern.variable('x')
_y = pattern.variable('y')
_z = pattern.variable('z')
_args = pattern.variable('args')
_name = pattern.variable('name')


def _decompile_stack(stack):
    if stack is None:
        return None
    head, args = stack
    if is_var(head) or head is HOLE or head is J:
        args = _decompile_args(args)
        return _from_stack((head, args))
    elif head is TOP:
        return TOP
    elif head is BOT:
        return BOT
    elif head is I:
        if args is None:
            x = _fresh()
            return FUN(x, x)
        else:
            return _decompile_stack(args)
    elif head is K:
        if args is None:
            x = _fresh()
            y = _fresh()
            return FUN(x, FUN(y, x))
        x, args = args
        if args is None:
            y = _fresh()
            return FUN(y, x)
        y, args = args
        return _decompile_stack((x, args))
    elif head is B:
        if args is None:
            x = _fresh()
            y = _fresh()
            z = _fresh()
            return FUN(x, FUN(y, FUN(z, APP(x, APP(y, z)))))
        x, args = args
        if args is None:
            y = _fresh()
            z = _fresh()
            xyz = _decompile_stack(_to_stack(x, APP(y, z), None))
            return FUN(y, FUN(z, xyz))
        y, args = args
        if args is None:
            z = _fresh()
            xyz = _decompile_stack(_to_stack(x, APP(y, z), None))
            return FUN(z, xyz)
        z, args = args
        return _decompile_stack(_to_stack(x, APP(y, z), args))
    elif head is C:
        if args is None:
            x = _fresh()
            y = _fresh()
            z = _fresh()
            return FUN(x, FUN(y, FUN(z, APP(APP(x, z), y))))
        x, args = args
        if args is None:
            y = _fresh()
            z = _fresh()
            xzy = _decompile_stack(_to_stack(x, z, y, None))
            return FUN(y, FUN(z, xzy))
        y, args = args
        if args is None:
            z = _fresh()
            xzy = _decompile_stack(_to_stack(x, z, y, None))
            return FUN(z, xzy)
        z, args = args
        return _decompile_stack(_to_stack(x, z, y, args))
    elif head is S:
        if args is None:
            x = _fresh()
            y = _fresh()
            z = _fresh()
            return FUN(x, FUN(y, FUN(z, APP(APP(x, z), APP(y, z)))))
        x, args = args
        if args is None:
            y = _fresh()
            z = _fresh()
            tx = _decompile(x)
            return FUN(y, FUN(z, APP(APP(tx, z), APP(y, z))))
        y, args = args
        if args is None:
            z = _fresh()
            tx = _decompile(x)
            ty = _decompile(y)
            return FUN(z, APP(APP(tx, z), APP(ty, z)))
        z, args = args
        if is_var(z):
            head = _decompile(APP(APP(x, z), APP(y, z)))
            args = _decompile_args(args)
            return _from_stack((head, args))
        v = _fresh()
        z = _decompile(z)
        xv = APP(x, v)
        yv = APP(y, v)
        head = LET(v, z, _decompile(APP(xv, yv)))
        args = _decompile_args(args)
        return _from_stack((head, args))
    else:
        raise ValueError('Cannot decompile: {}'.format(head))


def _decompile(code):
    stack = _to_stack(code, None)
    return _decompile_stack(stack)


def decompile(code):
    global FRESH_ID
    FRESH_ID = 0
    return _decompile(code)
