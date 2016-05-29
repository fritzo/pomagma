'''DSL translating from lambda-let notation to SKJ.'''

from pomagma.compiler.util import memoize_args
from pomagma.reducer import io
from pomagma.reducer.code import I, K, B, C, S, BOT, APP, JOIN, VAR
from pomagma.reducer.code import parse
from pomagma.reducer.code import serialize
from pomagma.util import TODO
import contextlib
import functools
import unification

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


# ----------------------------------------------------------------------------
# Sugar

def app(*args):
    if len(args) < 2:
        raise SyntaxError('Too few arguments: app{}'.format(args))
    result = args[0]
    for arg in args[1:]:
        result = APP(result, arg)
    return result


def join(*args):
    if not args:
        return BOT
    result = args[0]
    for arg in args[1:]:
        result = APP(result, arg)
    return result


lhs = unification.var('lhs')
rhs = unification.var('rhs')
app_pattern = APP(lhs, rhs)
join_pattern = JOIN(lhs, rhs)


@memoize_args
def try_abstract(var, body):
    if body is var:
        return I  # Rule I.
    match = unification.unify(app_pattern, body)
    if match:
        lhs_abs = try_abstract(var, match[lhs])
        rhs_abs = try_abstract(var, match[rhs])
        if lhs_abs is None:
            if rhs_abs is None:
                return None  # Rule K.
            elif rhs_abs is I:
                return match[lhs]  # Rule eta.
            else:
                return app(B, match[lhs], rhs_abs)  # Rule B.
        else:
            if rhs_abs is None:
                return app(C, lhs_abs, match[rhs])  # Rule C.
            else:
                return app(S, lhs_abs, rhs_abs)  # Rule S.
    match = unification.unify(join_pattern, body)
    if match:
        lhs_abs = try_abstract(var, match[lhs])
        rhs_abs = try_abstract(var, match[rhs])
        if lhs_abs is None:
            if rhs_abs is None:
                return None  # Rule K.
            else:
                return JOIN(APP(K, match[lhs]), rhs_abs)  # Rule JOIN.
        else:
            if rhs_abs is None:
                return JOIN(lhs_abs, APP(K, match[rhs]))  # Rule JOIN.
            else:
                return JOIN(lhs_abs, rhs_abs)  # Rule JOIN.
    return None  # Rule K.


def abstract(var, body):
    result = try_abstract(var, body)
    return APP(K, body) if result is None else result


def fun(*args):
    if len(args) < 1:
        raise SyntaxError('Too few arguments: fun{}'.format(args))
    result = args[-1]
    for arg in reversed(args[:-1]):
        result = abstract(arg, result)
    return result


# ----------------------------------------------------------------------------
# Wrappers for intro forms

_arg1 = VAR('_arg1')
_arg2 = VAR('_arg2')

succ = fun(_arg1, io.succ(_arg1))
pair = fun(_arg1, _arg2, io.pair(_arg1, _arg2))
inl = fun(_arg1, io.inl(_arg1))
inr = fun(_arg1, io.inr(_arg1))
some = fun(_arg1, io.some(_arg1))
cons = fun(_arg1, _arg2, io.cons(_arg1, _arg2))


# ----------------------------------------------------------------------------
# Programs

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


def program(*types):
    """Program decorator specifying types."""
    if len(types) < 2:
        raise SyntaxError('Too few types: program{}'.format(types))
    if len(types) > 2:
        TODO('automatically curry')
    tp_in, tp_out = types

    def decorator(py_fun):
        try:
            value = py_fun(_arg1)
        except NotImplementedError:
            value = BOT
        impl = fun(_arg1, value)
        program = Program(tp_in, tp_out, impl)
        return functools.wraps(py_fun)(program)

    return decorator
