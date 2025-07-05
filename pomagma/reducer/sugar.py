"""DSL translating from lambda-let notation to SKJ."""

import functools
import inspect
from collections.abc import Callable
from typing import Any

from pomagma.reducer.bohm import convert
from pomagma.reducer.syntax import NVAR, Term, free_vars, quoted_vars
from pomagma.reducer.util import LOG


@functools.singledispatch
def as_term(arg: Any) -> Term:
    raise NotImplementedError(f"Cannot convert to term: {arg}")


@as_term.register
def _as_term_term(arg: Term) -> Term:
    return arg


################################################################
# Compiler


def _compile(fun: Callable, actual_fun: Callable | None = None) -> Term:
    """Convert lambdas to terms using Higher Order Abstract Syntax [1].

    [1] Pfenning, Elliot (1988) "Higher-order abstract syntax"
      https://www.cs.cmu.edu/~fp/papers/pldi88.pdf

    """
    if actual_fun is None:
        actual_fun = fun
    args, vargs, kwargs, defaults = inspect.getfullargspec(actual_fun)[:4]
    if vargs or kwargs or defaults:
        source = inspect.getsource(actual_fun)
        raise SyntaxError(f"Unsupported signature: {source}")
    symbolic_args = list(map(NVAR, args))
    symbolic_result = fun(*symbolic_args)
    LOG.debug(f"compiling {fun}{tuple(symbolic_args)} = {symbolic_result}")
    term = as_term(symbolic_result)
    for var in reversed(symbolic_args):
        term = convert.FUN(var, term)
    return term


class _Combinator:
    """
    Class for results of the @combinator decorator.

    WARNING recursive combinators must use this via the @combinator
    decorator, so that a recursion guard can be inserted prior to
    compilation.
    """

    _fun: Callable
    _calling: bool
    _term: Term
    __name__: str

    def __init__(self, fun: Callable) -> None:
        functools.update_wrapper(self, fun)
        self._fun = fun
        self._calling = False

    def __repr__(self) -> str:
        return repr(self.term)

    def __str__(self) -> str:
        return self.__name__

    def __call__(self, *args: Any) -> Term:
        term = self.term  # Compile at first call.
        if self._calling:  # Disallow reentrance.
            return app(term, *args)
        self._calling = True
        # TODO handle variable number of arguments.
        result = self._fun(*args)
        self._calling = False
        return as_term(result)

    def __or__(*args: Any) -> Term:
        return join_(args)

    @property
    def term(self) -> Term:
        try:
            return self._term
        except AttributeError:
            self._compile()
            return self._term

    def _compile(self) -> None:
        assert not hasattr(self, "_term")

        # Compile without recursion.
        var = NVAR(f"_{self.__name__}")
        self._term = var
        term = _compile(self, actual_fun=self._fun)

        # Handle recursion.
        if var in quoted_vars(term):
            # FIXME QFUN is not defined.
            term = qrec(convert.QFUN(var, term))  # type: ignore[attr-defined]
        elif var in free_vars(term):
            term = rec(convert.FUN(var, term))

        # Check that result has no free variables.
        free = free_vars(term)
        if free:
            raise SyntaxError(
                "Unbound variables: {}".format(" ".join(str(v[1]) for v in free))
            )

        self._term = term


def combinator(arg: Any) -> _Combinator:
    if isinstance(arg, _Combinator):
        return arg
    if not callable(arg):
        raise SyntaxError(f"Cannot apply @combinator to {arg}")
    return _Combinator(arg)


@as_term.register
def _as_term_combinator(arg: _Combinator) -> Term:
    return arg.term


@as_term.register
def _as_term_callable(arg: Callable) -> Term:
    return _compile(arg)


################################################################
# Sugar


def app(*args: Any) -> Term:
    if not args:
        raise SyntaxError(f"Too few arguments: app{args}")
    result = as_term(args[0])
    for arg in args[1:]:
        result = convert.APP(result, as_term(arg))
    return result


Term.__call__ = app  # type: ignore[invalid-assignment]


def join_(*args: Any) -> Term:
    if not args:
        return convert.BOT
    result = as_term(args[0])
    for arg in args[1:]:
        result = convert.JOIN(result, as_term(arg))
    return result


Term.__or__ = join_  # type: ignore[invalid-assignment]


def quote(arg: Any) -> Term:
    return convert.QUOTE(as_term(arg))


def qapp(*args: Any) -> Term:
    if len(args) < 2:
        raise SyntaxError(f"Too few arguments: qapp{args}")
    result = as_term(args[0])
    for arg in args[1:]:
        result = convert.QAPP(result, as_term(arg))
    return result


def rec(fun: Callable) -> Term:
    fxx = _compile(lambda x: app(fun, x(x)))
    return fxx(fxx)


def qrec(fun: Callable) -> Term:
    fxx = _compile(lambda qx: app(fun, qapp(qx, qapp(convert.QQUOTE, qx))))
    return fxx(convert.QUOTE(fxx))


def typed(*types: Any) -> Callable:
    """Type annotation.

    The final type is the output type.

    """
    if len(types) < 1:
        raise SyntaxError(f"Too few arguments: typed{types}")
    if len(types) > 3:
        raise NotImplementedError(f"Too many arguments: typed{types}")
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
            arg = arg_types[0](arg)  # type: ignore[index]
            return result_type(fun(arg))

        return typed_fun

    def decorator_2(fun):
        @functools.wraps(fun)
        def typed_fun(arg0, arg1):
            arg0 = arg_types[0](arg0)  # type: ignore[index]
            arg1 = arg_types[1](arg1)  # type: ignore[index]
            return result_type(fun(arg0, arg1))

        return typed_fun

    return [decorator_0, decorator_1, decorator_2][len(arg_types)]


def symmetric(fun: Callable) -> Callable:
    @functools.wraps(fun)
    def symmetric_fun(x, y):
        return join_(fun(x, y), fun(y, x))

    return symmetric_fun


def let(defn: Term, var_body: Callable[[Any], Term]) -> Term:
    return app(var_body, defn)
