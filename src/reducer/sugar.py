'''DSL translating from lambda-let notation to SKJ.'''

from pomagma.compiler.util import memoize_args
from pomagma.reducer.code import I, K, B, C, S, BOT, APP, JOIN, VAR
from pomagma.reducer.util import LOG
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


def occurs(var, body):
    return abstract(var, body) is not None


# ----------------------------------------------------------------------------
# Compiler

def _compile(fun, actual_fun=None):
    if actual_fun is None:
        actual_fun = fun
    args, vargs, kwargs, defaults = inspect.getargspec(actual_fun)
    if vargs or kwargs or defaults:
        source = inspect.getsource(actual_fun)
        raise SyntaxError('Unsupported signature: {}'.format(source))
    symbolic_args = map(VAR, args)
    try:
        symbolic_result = fun(*symbolic_args)
    except NotImplementedError:
        symbolic_result = BOT
    LOG.debug('compiling {}{} = {}'.format(
        fun, tuple(symbolic_args), symbolic_result))
    code = as_code(symbolic_result)
    for var in reversed(symbolic_args):
        code = abstract(var, code)
    return code


class Untyped(object):

    def __init__(self, fun):
        functools.update_wrapper(self, fun)
        self._fun = fun
        self._calling = False

    def __repr__(self):
        return self.__name__

    def __call__(self, *args):
        code = self.code  # Compile at first call.
        if self._calling:  # Disallow reentrance.
            return app(code, *args)
        else:
            self._calling = True
            result = self._fun(*args)
            self._calling = False
            return result

    @property
    def code(self):
        try:
            return self._code
        except AttributeError:
            self._compile()
            return self._code

    def _compile(self):
        assert not hasattr(self, '_code')
        var = VAR('_fun{}'.format(id(self)))
        self._code = var

        code = _compile(self, actual_fun=self._fun)
        rec_code = try_abstract(var, code)
        if rec_code is not None:
            code = rec(rec_code)

        self._code = code


def untyped(arg):
    if isinstance(arg, Untyped):
        return arg
    if not callable(arg):
        raise SyntaxError('Cannot apply @untyped to {}'.format(arg))
    return Untyped(arg)


def as_code(arg):
    if isinstance(arg, Untyped):
        return arg.code
    elif callable(arg):
        return _compile(arg)
    else:
        return arg


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


def rec(fun):

    def fxx(x):
        return app(fun, app(x, x))

    return app(fxx, fxx)


def symmetric(fun):

    # TODO
    # @functools.wraps(fun)
    # def symmetric_fun(x, y):
    #     return join(fun(x, y), fun(y, x))

    return fun
