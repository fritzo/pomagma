"""Wrapping term to use SKJ programs from python."""

import contextlib
import functools

from pomagma.reducer import data
from pomagma.reducer.sugar import app, combinator

ENGINE = None  # Must have a method .reduce(term, budget=0) -> term.
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


class Program:
    def __init__(self, encoders, decoder, fun):
        functools.update_wrapper(self, fun)
        self._encoders = encoders
        self._decoder = decoder
        self._untyped = combinator(fun)

    def __repr__(self):
        return self.__name__

    @property
    def combinator(self):
        return self._untyped

    def __call__(self, *args):
        if len(args) != len(self._encoders):
            raise TypeError(
                f"{self.__name__} takes {len(self._encoders)} arguments ({len(args)} given)"
            )
        if ENGINE is None:
            raise RuntimeError("No engine specified")
        term_args = [encode(arg) for encode, arg in zip(self._encoders, args)]
        term_in = app(self.combinator.term, *term_args)
        term_out = ENGINE.reduce(term_in)
        data.check_for_errors(term_out)
        return self._decoder(term_out)


def program(*types):
    """Program decorator specifying types.

    All but the last type are inputs; the last type is the output type.

    """
    if not types:
        raise SyntaxError(f"No output type: program{types}")
    tps_in = types[:-1]
    tp_out = types[-1]
    encoders = list(map(data.encoder, tps_in))
    decoder = data.decoder(tp_out)
    return lambda fun: Program(encoders, decoder, fun)
