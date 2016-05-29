"""Wrapping code to use SKJ programs from python."""

from itertools import izip
from pomagma.reducer import io
from pomagma.reducer.code import parse
from pomagma.reducer.code import serialize
from pomagma.reducer.sugar import untyped
from pomagma.reducer.sugar import app
import contextlib
import functools

ENGINE = None  # Must have a method .reduce(code, budget=0) -> code.
BUDGET = 10000


@contextlib.contextmanager
def using_engine(engine, budget=None):
    global ENGINE
    global BUDGET
    old_engine = ENGINE
    ENGINE = engine
    if budget is not None:
        old_budget = BUDGET
        BUDGET = budget
    yield
    assert ENGINE == engine
    ENGINE = old_engine
    if budget is not None:
        assert BUDGET == budget
        BUDGET = old_budget


def execute(code_in):
    if ENGINE is None:
        raise RuntimeError('No engine specified')
    polish_in = serialize(code_in)
    polish_out = ENGINE.reduce(polish_in, budget=BUDGET)['code']
    code_out = parse(polish_out)
    return code_out


class Program(object):

    def __init__(self, encoders, decoder, fun):
        functools.update_wrapper(self, fun)
        self._encoders = encoders
        self._decoder = decoder
        self._untyped = untyped(fun)

    @property
    def untyped(self):
        return self._untyped

    def __call__(self, *args):
        if len(args) != len(self._encoders):
            raise TypeError('{} takes {} arguments ({} given)'.format(
                self.__name__, len(self._encoders), len(args)))
        code_args = [encode(arg) for encode, arg in izip(self._encoders, args)]
        code_in = app(self.untyped.code, *code_args)
        code_out = execute(code_in)
        data_out = self._decode(code_out)
        return data_out


def program(*types):
    """Program decorator specifying types.

    All but the last type are inputs; the last type is the output type.

    """
    if not types:
        raise SyntaxError('No output type: program{}'.format(types))
    tps_in = types[:-1]
    tp_out = types[-1]
    encoders = map(io.encoder, tps_in)
    decoder = io.decoder(tp_out)
    return lambda fun: Program(encoders, decoder, fun)
