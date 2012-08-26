import os
import functools
from math import log, exp
from contextlib import contextmanager


def TODO(message=''):
    raise NotImplementedError('TODO {}'.format(message))


def union(sets):
    sets = list(sets)
    if sets:
        return set.union(*sets)
    else:
        return set()


def set_with(set_, element):
    result = set(set_)
    result.add(element)
    return result


def set_without(set_, element):
    result = set(set_)
    result.remove(element)
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


def methodof(class_):
    def deco(fun):
        setattr(class_, fun.__name__, fun)
    return deco


@contextmanager
def line_writer(filename):
    succeded = False
    try:
        with open(filename, 'w') as out:
            def write(line=None):
                if line:
                    out.write(line)
                out.write('\n')
            yield write
        succeded = True
    finally:
        if not succeded:
            if os.path.exists(filename):
                os.remove(filename)
