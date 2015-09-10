import os
import glob
import functools
import itertools
from itertools import izip
from math import log
from math import exp
import pomagma.util

function = type(lambda x: x)


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


def eval_float44(num):
    '''
    8 bit nonnegative floating point = 4 bit significand + 4 bit exponent.
    Gradually increase from 0 to about 1e6 over inputs 0...255
    such that output is monotone increasing and has small relative increase.
    '''
    assert isinstance(num, int) and 0 <= num and num < 256, num
    nibbles = (num % 16, num / 16)
    return (nibbles[0] + 16) * 2 ** nibbles[1] - 16


def eval_float53(num):
    '''
    8 bit nonnegative floating point = 5 bit significand + 3 bit exponent.
    Gradually increase from 0 to about 8e3 over inputs 0...255
    such that output is monotone increasing and has small relative increase.
    '''
    assert isinstance(num, int) and 0 <= num and num < 256, num
    nibbles = (num % 32, num / 32)
    return (nibbles[0] + 32) * 2 ** nibbles[1] - 32


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


def get_consts(thing):
    if hasattr(thing, 'consts'):
        return thing.consts
    else:
        return union(get_consts(i) for i in thing)


@inputs(dict)
def permute_symbols(perm, thing):
    if not perm:
        return thing
    elif hasattr(thing, 'permute_symbols'):
        return thing.permute_symbols(perm)
    elif hasattr(thing, '__iter__'):
        return thing.__class__(permute_symbols(perm, i) for i in thing)
    elif isinstance(thing, (int, float)):
        return thing
    else:
        raise ValueError('cannot permute_symbols of {}'.format(thing))


def memoize_modulo_renaming_constants(fun):
    cache = {}

    @functools.wraps(fun)
    def cached(*args):
        consts = sorted(c.name for c in get_consts(args))
        result = None
        for permuted_consts in itertools.permutations(consts):
            perm = {i: j for i, j in izip(consts, permuted_consts) if i != j}
            permuted_args = permute_symbols(perm, args)
            try:
                permuted_result = cache[permuted_args]
            except KeyError:
                continue
            logger('{}: using cache via {}', fun.__name__, perm)
            inverse = {j: i for i, j in perm.iteritems()}
            return permute_symbols(inverse, permuted_result)
        logger('{}: compute', fun.__name__)
        result = fun(*args)
        cache[args] = result
        return result

    return cached


def memoize_make(cls):
    cls.make = staticmethod(memoize_args(cls))
    return cls
