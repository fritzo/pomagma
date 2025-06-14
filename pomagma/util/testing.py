import contextlib
import functools
import inspect

import pytest


def for_each(examples):
    def decorator(fun):
        args, vargs, kwargs, defaults = inspect.getfullargspec(fun)[:4]
        if vargs or kwargs or defaults:
            raise TypeError(
                "\n  ".join(
                    [
                        f"Unsupported signature: {fun}",
                        f"args = {args}",
                        f"vargs = {vargs}",
                        f"kwargs = {kwargs}",
                        f"defaults = {defaults}",
                    ]
                )
            )
        argnames = ",".join(args)
        return pytest.mark.parametrize(argnames, examples)(fun)

    return decorator


def for_each_kwargs(examples):
    def decorator(fun):
        args, vargs, kwargs, defaults = inspect.getfullargspec(fun)[:4]
        if vargs or kwargs:
            raise TypeError(
                "\n  ".join(
                    [
                        f"Unsupported signature: {fun}",
                        f"args = {args}",
                        f"vargs = {vargs}",
                        f"kwargs = {kwargs}",
                        f"defaults = {defaults}",
                    ]
                )
            )

        # FIXME This wrapper pollutes the test log.
        @functools.wraps(fun)
        def wrapped_fun(example):
            example = {k: v for k, v in list(example.items()) if k in args}
            return fun(**example)

        return pytest.mark.parametrize("example", examples)(wrapped_fun)

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


def xfail_param(*args, reason="FIXME", **kwargs):
    """Helper to create pytest.param with xfail mark."""
    return pytest.param(*args, marks=pytest.mark.xfail(reason=reason, **kwargs))


def skip_param(*args, reason="SKIP", **kwargs):
    """Helper to create pytest.param with skip mark."""
    return pytest.param(*args, marks=pytest.mark.skip(reason=reason, **kwargs))
