'''DSL translating from lambda-let notation to SKJ.'''

from pomagma.reducer.code import HOLE, BOT, QAPP, VAR, APP, JOIN, QUOTE
from pomagma.reducer.code import free_vars
from pomagma.reducer.transforms import try_abstract, abstract
from pomagma.reducer.util import LOG
import functools
import inspect


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
        symbolic_result = HOLE
    LOG.debug('compiling {}{} = {}'.format(
        fun, tuple(symbolic_args), symbolic_result))
    code = as_code(symbolic_result)
    for var in reversed(symbolic_args):
        code = abstract(var, code)
    return code


class _Combinator(object):
    '''
    Class for results of the @combinator decorator.

    WARNING recursive combinators must use this via the @combinator decorator,
    so that a recursion guard can be inserted prior to compilation.
    '''

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
        var = VAR(self.__name__)
        self._code = var

        code = _compile(self, actual_fun=self._fun)
        rec_code = try_abstract(var, code)
        if rec_code is not None:
            code = rec(rec_code)

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


def quote(arg):
    return QUOTE(as_code(arg))


def qapp(*args):
    args = map(as_code, args)
    if len(args) < 2:
        raise SyntaxError('Too few arguments: qapp{}'.format(args))
    result = args[0]
    for arg in args[1:]:
        result = APP(APP(QAPP, result), arg)
    return result


def rec(fun):
    fxx = _compile(lambda x: app(fun, app(x, x)))
    return app(fxx, fxx)


def symmetric(fun):

    @functools.wraps(fun)
    def symmetric_fun(x, y):
        return join(fun(x, y), fun(y, x))

    return symmetric_fun
