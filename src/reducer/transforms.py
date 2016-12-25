"""Code-to-code transforms."""

__all__ = ['try_abstract', 'abstract', 'decompile']

from pomagma.compiler.util import memoize_args
from pomagma.reducer import pattern
from pomagma.reducer.code import TOP, BOT, I, K, B, C, S
from pomagma.reducer.code import NVAR, APP, JOIN, QUOTE, FUN
from pomagma.reducer.code import is_atom, is_nvar, is_app, is_join, is_quote
from pomagma.reducer.code import is_fun


# ----------------------------------------------------------------------------
# Abstraction

@memoize_args
def try_abstract(var, body):
    """Returns \\var.body if var occurs in body, else None."""
    if not is_nvar(var):
        raise NotImplementedError('Only variables can be abstracted')
    if body is var:
        return I  # Rule I
    elif is_app(body):
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
    elif is_join(body):
        lhs = body[1]
        rhs = body[2]
        lhs_abs = try_abstract(var, lhs)
        rhs_abs = try_abstract(var, rhs)
        if lhs_abs is None:
            if rhs_abs is None:
                return None  # Rule K
            else:
                return JOIN(APP(K, lhs), rhs_abs)  # Rule JOIN-K
        else:
            if rhs_abs is None:
                return JOIN(lhs_abs, APP(K, rhs))  # Rule JOIN-K
            else:
                return JOIN(lhs_abs, rhs_abs)  # Rule JOIN
    else:
        return None  # Rule K


def abstract(var, body):
    """APP,JOIN,TOP,BOT,I,K,B,C,S,eta-abstraction algorithm."""
    result = try_abstract(var, body)
    if result is not None:
        return result
    elif body in (TOP, BOT):
        return body  # Rules TOP, BOT
    else:
        return APP(K, body)  # Rule K


# ----------------------------------------------------------------------------
# Definition as lazy substitution

def define(var, defn, body):
    if not is_nvar(var):
        raise NotImplementedError('Only variables can be abstracted')
    if is_atom(body):
        return body
    elif is_nvar(body):
        if body is var:
            return defn
        else:
            return body
    elif is_app(body):
        lhs = body[1]
        rhs = body[2]
        lhs_abs = try_abstract(var, lhs)
        rhs_abs = try_abstract(var, rhs)
        if lhs_abs is None:
            if rhs_abs is None:
                return body
            else:
                return APP(lhs, define(var, defn, rhs))
        else:
            if rhs_abs is None:
                return APP(define(var, defn, lhs), rhs)
            else:
                return APP(APP(APP(S, lhs_abs), rhs_abs), defn)
    elif is_join(body):
        lhs = body[1]
        rhs = body[2]
        lhs_abs = try_abstract(var, lhs)
        rhs_abs = try_abstract(var, rhs)
        if lhs_abs is None:
            if rhs_abs is None:
                return body
            else:
                return JOIN(lhs, define(var, defn, rhs))
        else:
            if rhs_abs is None:
                return JOIN(define(var, defn, lhs), rhs)
            else:
                return APP(JOIN(lhs_abs, rhs_abs), defn)
    elif is_quote(body):
        arg = body[1]
        return QUOTE(define(var, defn, arg))
    else:
        raise ValueError(body)


# ----------------------------------------------------------------------------
# Eager substitution

def substitute(var, defn, body):
    if not is_nvar(var):
        raise NotImplementedError('Only variables can be abstracted')
    if is_atom(body):
        return body
    elif is_nvar(body):
        if body is var:
            return defn
        else:
            return body
    elif is_app(body):
        lhs = substitute(var, defn, body[1])
        rhs = substitute(var, defn, body[2])
        return APP(lhs, rhs)
    elif is_join(body):
        lhs = substitute(var, defn, body[1])
        rhs = substitute(var, defn, body[2])
        return JOIN(lhs, rhs)
    elif is_quote(body):
        arg = body[1]
        return QUOTE(substitute(var, defn, arg))
    else:
        raise ValueError(body)


# ----------------------------------------------------------------------------
# Symbolic compiler : FUN -> I,K,B,C,S

def compile_(code):
    if is_atom(code):
        return code
    elif is_nvar(code):
        return code
    elif is_app(code):
        x = compile_(code[1])
        y = compile_(code[2])
        return APP(x, y)
    elif is_join(code):
        x = compile_(code[1])
        y = compile_(code[2])
        return JOIN(x, y)
    elif is_quote(code):
        arg = compile_(code[1])
        return QUOTE(arg)
    elif is_fun(code):
        var = code[1]
        body = compile_(code[2])
        return abstract(var, body)
    else:
        raise ValueError('Cannot compile_: {}'.format(code))


# ----------------------------------------------------------------------------
# Symbolic decompiler : I,K,B,C,S -> FUN

FRESH_ID = 0
FRESH_VARS = map(NVAR, 'abcdefghijklmnopqrstuvwxyz')
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
    if is_nvar(head):
        args = _decompile_args(args)
        return _from_stack((head, args))
    elif is_join(head):
        lhs = _decompile(head[1])
        rhs = _decompile(head[2])
        args = _decompile_args(args)
        return _from_stack((JOIN(lhs, rhs), args))
    elif is_quote(head):
        arg = _decompile(head[1])
        args = _decompile_args(args)
        return _from_stack((QUOTE(arg), args))
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
        if is_nvar(z):
            head = _decompile(APP(APP(x, z), APP(y, z)))
            args = _decompile_args(args)
            return _from_stack((head, args))
        v = _fresh()
        z = _decompile(z)
        xv = APP(x, v)
        yv = APP(y, v)
        head = APP(FUN(v, _decompile(APP(xv, yv))), z)
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
