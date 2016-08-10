import contextlib
import functools
import inspect
import pytest


def for_each(examples):

    def decorator(fun):
        args, vargs, kwargs, defaults = inspect.getargspec(fun)
        if vargs or kwargs or defaults:
            raise TypeError('Unsupported signature: {}'.format(fun))
        argnames = ','.join(args)
        return pytest.mark.parametrize(argnames, examples)(fun)

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


@contextlib.contextmanager
def xfail_if_not_implemented():
    try:
        yield
    except NotImplementedError as e:
        pytest.xfail(reason=str(e))


@contextlib.contextmanager
def skip_if_not_implemented():
    try:
        yield
    except NotImplementedError as e:
        pytest.skip(str(e))
