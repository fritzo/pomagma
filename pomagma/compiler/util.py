import atexit
import contextlib
import functools
import glob
import itertools
import os
import sys
from collections.abc import Callable
from math import exp, log
from typing import Generic, ParamSpec, TypeVar
from weakref import WeakKeyDictionary

import pomagma.util

function = type(lambda x: x)

_A = ParamSpec("_A")
_B = TypeVar("_B")
_C = TypeVar("_C")
_T = TypeVar("_T")


def intern_keys(string_dict: dict[str, _B]) -> dict[str, _B]:
    return {sys.intern(str(key)): val for key, val in list(string_dict.items())}


def DELETE(*args, **kwargs):
    raise ValueError("deleted method")


def logger(message, *args):
    if pomagma.util.LOG_LEVEL >= pomagma.util.LOG_LEVEL_DEBUG:
        print("#", message.format(*args))


class sortedset(set, Generic[_T]):
    __slots__ = ["_sorted", "_hash"]

    _sorted: tuple[_T]
    _hash: int

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
    return -float("inf")


def eval_float44(num):
    """
    8 bit nonnegative floating point = 4 bit significand + 4 bit exponent.
    Gradually increase from 0 to about 1e6 over inputs 0...255
    such that output is monotone increasing and has small relative increase.
    """
    assert isinstance(num, int) and 0 <= num and num < 256, num
    nibbles = (num % 16, num // 16)
    return (nibbles[0] + 16) * 2 ** nibbles[1] - 16


def eval_float53(num):
    """
    8 bit nonnegative floating point = 5 bit significand + 3 bit exponent.
    Gradually increase from 0 to about 8e3 over inputs 0...255
    such that output is monotone increasing and has small relative increase.
    """
    assert isinstance(num, int) and 0 <= num and num < 256, num
    nibbles = (num % 32, num // 32)
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
    return glob.glob(os.path.join(pomagma.util.THEORY, "*.theory"))


MEMOIZED_CACHES = {}


def memoize_arg(fun: Callable[[_B], _C]) -> Callable[[_B], _C]:
    cache: dict[_B, _C] = {}

    @functools.wraps(fun)
    def memoized(arg: _B) -> _C:
        try:
            return cache[arg]
        except KeyError:
            result = fun(arg)
            cache[arg] = result
            return result

    MEMOIZED_CACHES[memoized] = cache
    return memoized


def memoize_args(fun: Callable[_A, _B]) -> Callable[_A, _B]:
    cache: dict[tuple, _B] = {}

    @functools.wraps(fun)
    def memoized(*args) -> _B:
        try:
            return cache[args]
        except KeyError:
            result = fun(*args)  # type: ignore[call-arg]
            cache[args] = result
            return result

    MEMOIZED_CACHES[memoized] = cache
    return memoized  # type: ignore[return-value]


@contextlib.contextmanager
def temp_memoize():
    base = MEMOIZED_CACHES.copy()
    yield
    for fun, cache in list(MEMOIZED_CACHES.items()):
        cache.clear()
        cache.update(base.get(fun, {}))


UNIQUE = {}


def unique(arg):
    return UNIQUE.get(arg, arg)


MEMOIZED_CACHES[unique] = UNIQUE


def unique_result(fun: Callable[_A, _B]) -> Callable[_A, _B]:
    @functools.wraps(fun)
    def decorated(*args, **kwargs):
        return unique(fun(*args, **kwargs))

    return decorated


def profile_memoized():
    sizes = [(len(cache), fun) for (fun, cache) in list(MEMOIZED_CACHES.items())]
    sizes.sort(reverse=True)
    sys.stderr.write("{: >10} {}\n".format("# entries", "memoized function"))
    sys.stderr.write("-" * 32 + "\n")
    for size, fun in sizes:
        if size > 0:
            sys.stderr.write(f"{size: >10} {fun.__module__}.{fun.__name__}\n")


if int(os.environ.get("POMAGMA_PROFILE_MEMOIZED", 0)):
    atexit.register(profile_memoized)


def get_consts(thing):
    if hasattr(thing, "consts"):
        return thing.consts
    return union(get_consts(i) for i in thing)


@inputs(dict)
def permute_symbols(perm, thing):
    if not perm:
        return thing
    if hasattr(thing, "permute_symbols"):
        return thing.permute_symbols(perm)
    if hasattr(thing, "__iter__"):
        return thing.__class__(permute_symbols(perm, i) for i in thing)
    if isinstance(thing, int | float):
        return thing
    raise ValueError(f"cannot permute_symbols of {thing}")


def memoize_modulo_renaming_constants(fun):
    cache = {}

    @functools.wraps(fun)
    def memoized(*args):
        consts = sorted(c.name for c in get_consts(args))
        result = None
        for permuted_consts in itertools.permutations(consts):
            perm = {i: j for i, j in zip(consts, permuted_consts) if i != j}
            permuted_args = permute_symbols(perm, args)
            try:
                permuted_result = cache[permuted_args]
            except KeyError:
                continue
            logger("{}: using cache via {}", fun.__name__, perm)
            inverse = {j: i for i, j in list(perm.items())}
            return permute_symbols(inverse, permuted_result)
        logger("{}: compute", fun.__name__)
        result = fun(*args)
        cache[args] = result
        return result

    MEMOIZED_CACHES[memoized] = cache
    return memoized


def weak_memoize_1(fun):
    """Weakly memoize a function of one argument. Kwargs are not memoized."""
    cache = WeakKeyDictionary()

    @functools.wraps(fun)
    def memoized(arg, **kwargs):
        if (result := cache.get(arg, None)) is not None:
            return result
        result = fun(arg, **kwargs)
        cache[arg] = result
        return result

    return memoized


def weak_memoize_2(fun):
    """Weakly memoize a function of one argument. Kwargs are not memoized."""
    caches = WeakKeyDictionary()

    @functools.wraps(fun)
    def memoized(arg1, arg2, **kwargs):
        if (cache := caches.get(arg1, None)) is None:
            cache = caches[arg1] = WeakKeyDictionary()
        if (result := cache.get(arg2, None)) is not None:
            return result
        result = fun(arg1, arg2, **kwargs)
        cache[arg2] = result
        return result

    return memoized


def memoize_weak_strong(fun):
    """
    Memoize a function weakly on the first argument, strongly on the second.
    Kwargs are not memoized.
    """
    caches = WeakKeyDictionary()

    @functools.wraps(fun)
    def memoized(arg1, arg2, **kwargs):
        if (cache := caches.get(arg1, None)) is None:
            cache = caches[arg1] = {}
        if (result := cache.get(arg2, None)) is not None:
            return result
        result = fun(arg1, arg2, **kwargs)
        cache[arg2] = result
        return result

    return memoized
