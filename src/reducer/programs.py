"""Wrapping code to use SKJ programs from python."""

from pomagma.reducer import io
from pomagma.reducer.code import BOT, VAR
from pomagma.reducer.code import parse
from pomagma.reducer.code import serialize
from pomagma.reducer.sugar import fun
from pomagma.util import TODO
import contextlib
import functools

DEFAULT_BUDGET = 10000
ENGINE = None  # Must have a method .reduce(code, budget=0) -> code.


@contextlib.contextmanager
def using_engine(engine):
    global ENGINE
    old_value = ENGINE
    ENGINE = engine
    yield
    assert ENGINE == engine
    ENGINE = old_value


class Program(object):

    def __init__(self, tp_in, tp_out, impl):
        self._encode = io.encoder(tp_in)
        self._decode = io.decoder(tp_out)
        self._impl = impl

    @property
    def impl(self):
        # TODO add type checks.
        return self._impl

    def __call__(self, data_in, engine=None, budget=DEFAULT_BUDGET):
        if engine is None:
            engine = ENGINE
        if engine is None:
            raise RuntimeError('No engine specified')
        code_in = self._encode(data_in)
        polish_in = serialize(code_in)
        polish_out = engine.reduce(polish_in)['code']
        code_out = parse(polish_out)
        data_out = self._decode(code_out)
        return data_out


_arg = VAR('_arg')


def program(*types):
    """Program decorator specifying types."""
    if len(types) < 2:
        raise SyntaxError('Too few types: program{}'.format(types))
    if len(types) > 2:
        TODO('automatically curry')
    tp_in, tp_out = types

    def decorator(py_fun):
        try:
            value = py_fun(_arg)
        except NotImplementedError:
            value = BOT
        impl = fun(_arg, value)
        program = Program(tp_in, tp_out, impl)
        return functools.wraps(py_fun)(program)

    return decorator
