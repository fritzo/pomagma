"""DSL translating from lambda-let notation to SKJ."""

import functools
import inspect

from pomagma.reducer.bohm import convert
from pomagma.reducer.syntax import NVAR, free_vars, quoted_vars
from pomagma.reducer.util import LOG


# ----------------------------------------------------------------------------
# Compiler

def _compile(fun, actual_fun=None):
    if actual_fun is None:
        actual_fun = fun
    args, vargs, kwargs, defaults = inspect.getargspec(actual_fun)
    if vargs or kwargs or defaults:
        source = inspect.getsource(actual_fun)
        raise SyntaxError('Unsupported signature: {}'.format(source))
    symbolic_args = map(NVAR, args)
    symbolic_result = fun(*symbolic_args)
    LOG.debug('compiling {}{} = {}'.format(
        fun, tuple(symbolic_args), symbolic_result))
    code = as_code(symbolic_result)
    for var in reversed(symbolic_args):
        code = convert.FUN(var, code)
    return code


class _Combinator(object):
    """Class for results of the @combinator decorator.

    WARNING recursive combinators must use this via the @combinator
    decorator, so that a recursion guard can be inserted prior to
    compilation.

    """

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
        var = NVAR('_{}'.format(self.__name__))
        self._code = var

        code = _compile(self, actual_fun=self._fun)
        if var in quoted_vars(code):
            code = qrec(convert.QFUN(var, code))
        elif var in free_vars(code):
            code = rec(convert.FUN(var, code))

        free = free_vars(code)
        if free:
            raise SyntaxError('Unbound variables: {}'.format(
                ' '.join(v[1] for v in free)))

        self._code = code


def combinator(arg):
    if isinstance(arg, _Combinator):
        return arg
    if not callable(arg):
        raise SyntaxError('Cannot apply @combinator to {}'.format(arg))
    return _Combinator(arg)


def as_code(arg):
    if isinstance(arg, _Combinator):
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
        result = convert.APP(result, arg)
    return result


def join_(*args):
    args = map(as_code, args)
    if not args:
        return convert.BOT
    result = args[0]
    for arg in args[1:]:
        result = convert.JOIN(result, arg)
    return result


def quote(arg):
    return convert.QUOTE(as_code(arg))


def qapp(*args):
    args = map(as_code, args)
    if len(args) < 2:
        raise SyntaxError('Too few arguments: qapp{}'.format(args))
    result = args[0]
    for arg in args[1:]:
        result = convert.APP(convert.APP(convert.QAPP, result), arg)
    return result


def rec(fun):
    fxx = _compile(lambda x: app(fun, app(x, x)))
    return app(fxx, fxx)


def qrec(fun):
    fxx = _compile(lambda qx: app(fun, qapp(qx, qapp(convert.QQUOTE, qx))))
    return app(fxx, convert.QUOTE(fxx))


def typed(*types):
    """Type annotation.

    The final type is the output type.

    """
    if len(types) < 1:
        raise SyntaxError('Too few arguments: typed{}'.format(types))
    result_type = types[-1]
    arg_types = types[:-1]

    def decorator_0(fun):

        @functools.wraps(fun)
        def typed_fun():
            return app(result_type, fun())

        return typed_fun

    def decorator_1(fun):

        @functools.wraps(fun)
        def typed_fun(arg):
            arg = app(arg_types[0], arg)
            return app(result_type, fun(arg))

        return typed_fun

    def decorator_2(fun):

        @functools.wraps(fun)
        def typed_fun(arg0, arg1):
            arg0 = app(arg_types[0], arg0)
            arg1 = app(arg_types[1], arg1)
            return app(result_type, fun(arg0, arg1))

        return typed_fun

    return [decorator_0, decorator_1, decorator_2][len(arg_types)]


def symmetric(fun):

    @functools.wraps(fun)
    def symmetric_fun(x, y):
        return join_(fun(x, y), fun(y, x))

    return symmetric_fun


def let(defn, var_body):
    return app(var_body, defn)
