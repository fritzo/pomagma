"""DSL translating from lambda-let notation to SKJ."""

import functools
import inspect

from pomagma.reducer.bohm import convert
from pomagma.reducer.syntax import NVAR, Term, free_vars, quoted_vars
from pomagma.reducer.util import LOG


# ----------------------------------------------------------------------------
# Compiler


def _compile(fun, actual_fun=None):
    """Convert lambdas to terms using Higher Order Abstract Syntax [1].

    [1] Pfenning, Elliot (1988) "Higher-order abstract syntax"
      https://www.cs.cmu.edu/~fp/papers/pldi88.pdf

    """
    if actual_fun is None:
        actual_fun = fun
    args, vargs, kwargs, defaults = inspect.getfullargspec(actual_fun)[:4]
    if vargs or kwargs or defaults:
        source = inspect.getsource(actual_fun)
        raise SyntaxError("Unsupported signature: {}".format(source))
    symbolic_args = list(map(NVAR, args))
    symbolic_result = fun(*symbolic_args)
    LOG.debug("compiling {}{} = {}".format(fun, tuple(symbolic_args), symbolic_result))
    term = as_term(symbolic_result)
    for var in reversed(symbolic_args):
        term = convert.FUN(var, term)
    return term


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
        return repr(self.term)

    def __str__(self):
        return self.__name__

    def __call__(self, *args):
        term = self.term  # Compile at first call.
        if self._calling:  # Disallow reentrance.
            return app(term, *args)
        else:
            self._calling = True
            # TODO handle variable number of arguments.
            result = self._fun(*args)
            self._calling = False
            return as_term(result)

    def __or__(*args):
        return join_(args)

    @property
    def term(self):
        try:
            return self._term
        except AttributeError:
            self._compile()
            return self._term

    def _compile(self):
        assert not hasattr(self, "_term")

        # Compile without recursion.
        var = NVAR("_{}".format(self.__name__))
        self._term = var
        term = _compile(self, actual_fun=self._fun)

        # Handle recursion.
        if var in quoted_vars(term):
            term = qrec(convert.QFUN(var, term))
        elif var in free_vars(term):
            term = rec(convert.FUN(var, term))

        # Check that result has no free variables.
        free = free_vars(term)
        if free:
            raise SyntaxError(
                "Unbound variables: {}".format(" ".join(v[1] for v in free))
            )

        self._term = term


def combinator(arg):
    if isinstance(arg, _Combinator):
        return arg
    if not callable(arg):
        raise SyntaxError("Cannot apply @combinator to {}".format(arg))
    return _Combinator(arg)


def as_term(arg):
    if isinstance(arg, Term):
        return arg
    elif isinstance(arg, _Combinator):
        return arg.term
    else:
        if not callable(arg):
            raise SyntaxError("Cannot convert to term: {}".format(arg))
        return _compile(arg)


# ----------------------------------------------------------------------------
# Sugar


def app(*args):
    args = list(map(as_term, args))
    if not args:
        raise SyntaxError("Too few arguments: app{}".format(args))
    result = args[0]
    for arg in args[1:]:
        result = convert.APP(result, arg)
    return result


Term.__call__ = app


def join_(*args):
    args = list(map(as_term, args))
    if not args:
        return convert.BOT
    result = args[0]
    for arg in args[1:]:
        result = convert.JOIN(result, arg)
    return result


Term.__or__ = join_


def quote(arg):
    return convert.QUOTE(as_term(arg))


def qapp(*args):
    args = list(map(as_term, args))
    if len(args) < 2:
        raise SyntaxError("Too few arguments: qapp{}".format(args))
    result = args[0]
    for arg in args[1:]:
        result = convert.QAPP(result, arg)
    return result


def rec(fun):
    fxx = _compile(lambda x: app(fun, x(x)))
    return fxx(fxx)


def qrec(fun):
    fxx = _compile(lambda qx: app(fun, qapp(qx, qapp(convert.QQUOTE, qx))))
    return fxx(convert.QUOTE(fxx))


def typed(*types):
    """Type annotation.

    The final type is the output type.

    """
    if len(types) < 1:
        raise SyntaxError("Too few arguments: typed{}".format(types))
    if len(types) > 3:
        raise NotImplementedError("Too many arguments: typed{}".format(types))
    result_type = types[-1]
    arg_types = types[:-1]

    def decorator_0(fun):
        @functools.wraps(fun)
        def typed_fun():
            return result_type(fun())

        return typed_fun

    def decorator_1(fun):
        @functools.wraps(fun)
        def typed_fun(arg):
            arg = arg_types[0](arg)
            return result_type(fun(arg))

        return typed_fun

    def decorator_2(fun):
        @functools.wraps(fun)
        def typed_fun(arg0, arg1):
            arg0 = arg_types[0](arg0)
            arg1 = arg_types[1](arg1)
            return result_type(fun(arg0, arg1))

        return typed_fun

    return [decorator_0, decorator_1, decorator_2][len(arg_types)]


def symmetric(fun):
    @functools.wraps(fun)
    def symmetric_fun(x, y):
        return join_(fun(x, y), fun(y, x))

    return symmetric_fun


def let(defn, var_body):
    return app(var_body, defn)
