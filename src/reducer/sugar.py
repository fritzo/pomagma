'''DSL translating from lambda-let notation to SKJ.'''

from pomagma.compiler.util import memoize_args
from pomagma.reducer.code import I, K, B, C, S, BOT, APP, JOIN, VAR
import functools
import inspect
import unification


# ----------------------------------------------------------------------------
# Abstraction

_lhs = unification.var('lhs')
_rhs = unification.var('rhs')
_app_pattern = APP(_lhs, _rhs)
_join_pattern = JOIN(_lhs, _rhs)


@memoize_args
def try_abstract(var, body):
    """Returns \\var.body if var occurs in body, else None."""
    if body is var:
        return I  # Rule I.
    match = unification.unify(_app_pattern, body)
    if match:
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
    match = unification.unify(_join_pattern, body)
    if match:
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
# Function decorator

def _compile(fun):
    if not callable(fun):
        return fun
    args, vargs, kwargs, defaults = inspect.getargspec(fun)
    if vargs or kwargs or defaults:
        source = inspect.getsource(fun)
        raise SyntaxError('Unsupported signature: {}'.format(source))
    symbolic_args = map(VAR, args)
    code = as_code(fun(*symbolic_args))
    for var in reversed(symbolic_args):
        code = abstract(var, code)
    return code


class Untyped(object):

    def __init__(self, fun):
        functools.update_wrapper(self, fun)
        self._fun = fun
        self._code = _compile(fun)

    def __call__(self, *args):
        return self._fun(*args)

    @property
    def code(self):
        return self._code


def untyped(arg):
    return Untyped(arg) if callable(arg) else arg


def as_code(arg):
    return arg.code if isinstance(arg, Untyped) else _compile(arg)


# ----------------------------------------------------------------------------
# Sugar

def app(*args):
    args = map(as_code, args)
    if len(args) < 2:
        raise SyntaxError('Too few arguments: app{}'.format(args))
    result = args[0]
    for arg in args[1:]:
        result = APP(result, arg)
    return result


def join(*args):
    args = map(as_code, args)
    if not args:
        return BOT
    result = args[0]
    for arg in args[1:]:
        result = JOIN(result, arg)
    return result


def fun(*args):
    args = map(as_code, args)
    if len(args) < 1:
        raise SyntaxError('Too few arguments: fun{}'.format(args))
    result = args[-1]
    for arg in reversed(args[:-1]):
        result = abstract(arg, result)
    return result
