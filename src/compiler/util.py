import os
import glob
import functools
from math import log
from math import exp
import pomagma.util

function = type(lambda x: x)


def TODO(message=''):
    raise NotImplementedError('TODO {}'.format(message))


def logger(message):
    if pomagma.util.LOG_LEVEL >= pomagma.util.LOG_LEVEL_DEBUG:
        print '#', message


def union(sets):
    sets = list(sets)
    if sets:
        return set.union(*sets)
    else:
        return set()


def set_with(set_, *elements):
    result = set(set_)
    for e in elements:
        result.add(e)
    return result


def set_without(set_, *elements):
    result = set(set_)
    for e in elements:
        result.remove(e)
    return result


def log_sum_exp(*args):
    shift = max(args)
    return log(sum(exp(arg - shift) for arg in args)) + shift


def inputs(*types):
    def deco(fun):
        @functools.wraps(fun)
        def typed(*args):
            for arg, typ in zip(args, types):
                assert isinstance(arg, typ)
            return fun(*args)
        return typed
    return deco


def methodof(class_, name=None):
    def deco(fun):
        if name is not None:
            fun.__name__ = name
        setattr(class_, fun.__name__, fun)
    return deco


def find_facts():
    return [
        os.path.abspath(f)
        for f in glob.glob(os.path.join(pomagma.util.THEORY, '*.facts'))
    ]


def find_rules():
    return [
        os.path.abspath(f)
        for f in glob.glob(os.path.join(pomagma.util.THEORY, '*.rules'))
    ]
