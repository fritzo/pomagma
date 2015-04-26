import os
import glob
import functools
from math import log
from math import exp
import pomagma.util

function = type(lambda x: x)


def TODO(message=''):
    raise NotImplementedError('TODO {}'.format(message))


def DELETE(*args, **kwargs):
    raise ValueError('deleted method')


def logger(message, *args):
    if pomagma.util.LOG_LEVEL >= pomagma.util.LOG_LEVEL_DEBUG:
        print '#', message.format(*args)


class sortedset(set):
    __slots__ = ['_sorted', '_hash']

    def __init__(self, *args, **kwargs):
        set.__init__(self, *args, **kwargs)
        self._sorted = tuple(sorted(set.__iter__(self)))
        self._hash = hash(self._sorted)

    def __iter__(self):
        return iter(self._sorted)

    def __and__(self, other):
        result = set(self)
        result &= other
        return result

    def __or__(self, other):
        result = set(self)
        result |= other
        return result

    def __sub__(self, other):
        result = set(self)
        result -= other
        return result

    def __xor__(self, other):
        result = set(self)
        result ^= other
        return result

    def __hash__(self):
        return self._hash

    # weak immutability
    update = DELETE
    difference_update = DELETE
    intersection_update = DELETE
    symmetric_difference_update = DELETE
    add = DELETE
    remove = DELETE
    discard = DELETE
    pop = DELETE
    __ior__ = DELETE
    __iand__ = DELETE
    __ixor__ = DELETE
    __isub__ = DELETE


def union(sets):
    result = set()
    for s in sets:
        result.update(s)
    return result


def set_with(set_, *elements):
    result = set(set_)
    for e in elements:
        result.add(e)
    return set_.__class__(result)


def set_without(set_, *elements):
    result = set(set_)
    for e in elements:
        result.remove(e)
    return set_.__class__(result)


def log_sum_exp(*args):
    if args:
        shift = max(args)
        return log(sum(exp(arg - shift) for arg in args)) + shift
    else:
        return -float('inf')


def inputs(*types):
    def deco(fun):
        @functools.wraps(fun)
        def typed(*args, **kwargs):
            for arg, typ in zip(args, types):
                assert isinstance(arg, typ), arg
            return fun(*args, **kwargs)
        return typed
    return deco


def methodof(class_, name=None):
    def deco(fun):
        if name is not None:
            fun.__name__ = name
        setattr(class_, fun.__name__, fun)
    return deco


def find_theories():
    return glob.glob(os.path.join(pomagma.util.THEORY, '*.theory'))


def memoize_arg(fun):
    cache = {}

    @functools.wraps(fun)
    def memoized(arg):
        try:
            return cache[arg]
        except KeyError:
            result = fun(arg)
            cache[arg] = result
            return result

    return memoized


def memoize_args(fun):
    cache = {}

    @functools.wraps(fun)
    def memoized(*args):
        try:
            return cache[args]
        except KeyError:
            result = fun(*args)
            cache[args] = result
            return result

    return memoized


def memoize_make(cls):
    cls.make = staticmethod(memoize_args(cls))
    return cls


def for_each(examples):

    def decorator(fun):

        def fun_one(i):
            fun(examples[i])

        @functools.wraps(fun)
        def decorated():
            for i in xrange(len(examples)):
                yield fun_one, i

        return decorated
    return decorator


def for_each_kwargs(examples):

    def decorator(fun):

        def fun_one(i):
            fun(**examples[i])

        @functools.wraps(fun)
        def decorated():
            for i in xrange(len(examples)):
                yield fun_one, i

        return decorated
    return decorator
