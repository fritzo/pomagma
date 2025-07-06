import atexit
import functools
import inspect
import logging
import os
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import ParamSpec, TypeVar

import pomagma.util

_A = ParamSpec("_A")
_B = TypeVar("_B")
Decorator = Callable[[Callable[_A, _B]], Callable[_A, _B]]


class UnreachableError(RuntimeError):
    pass


def trool_fuse(args):
    """Combine according to:

          | None  True  False
    ------+------------------
     None | None  True  False
     True | True  True  error
    False | False error False

    """
    result = None
    for arg in args:
        if arg is not None:
            if result is None:
                result = arg
            elif result is not arg:
                raise ValueError(f"Incompatible: {result} vs {arg}")
    return result


def trool_all(args: Iterable[bool | None]) -> bool | None:
    """Combine according to:

          | None  True  False
    ------+------------------
     None | None  None  False
     True | None  True  False
    False | False False False

    """
    result = True
    for arg in args:
        if arg is False:
            return False
        if arg is None:
            result = None
    return result


def trool_any(args: Iterable[bool | None]) -> bool | None:
    """Combine according to:

          | None  True  False
    ------+------------------
     None | None  True  None
     True | True  True  True
    False | None  True  False

    """
    result = False
    for arg in args:
        if arg is True:
            return True
        if arg is None:
            result = None
    return result


def stack_to_list(stack):
    result = []
    while stack is not None:
        arg, stack = stack
        result.append(arg)
    return result


def list_to_stack(args):
    assert isinstance(args, list), args
    stack = None
    for arg in reversed(args):
        stack = arg, stack
    return stack


def iter_stack(stack):
    while stack is not None:
        arg, stack = stack
        yield arg


################################################################
# Logging

LOG_LEVELS = {
    pomagma.util.LOG_LEVEL_ERROR: logging.ERROR,
    pomagma.util.LOG_LEVEL_WARNING: logging.WARNING,
    pomagma.util.LOG_LEVEL_INFO: logging.INFO,
    pomagma.util.LOG_LEVEL_DEBUG: logging.DEBUG,
}


class IndentingFormatter(logging.Formatter):
    def __init__(self):
        logging.Formatter.__init__(self, "%(indent)s %(message)s")
        self.min_indent = 99999999

    def format(self, record):
        stack = inspect.stack()
        indent = len(stack)
        if indent < self.min_indent:
            self.min_indent = indent
        indent -= self.min_indent
        record.indent = " " * indent
        return logging.Formatter.format(self, record)


LOG = logging.getLogger(__name__)
LOG.setLevel(LOG_LEVELS[pomagma.util.LOG_LEVEL])
handler = logging.StreamHandler()
handler.setFormatter(IndentingFormatter())
LOG.addHandler(handler)


def _logged(*format_args, **format_kwargs) -> Decorator:
    formatters = dict(format_kwargs)
    formatters.update(dict(enumerate(format_args)))  # type: ignore[arg-type]

    def decorator(fun: Callable[_A, _B]) -> Callable[_A, _B]:
        @functools.wraps(fun)
        def decorated(*args: _A.args, **kwargs: _A.kwargs) -> _B:
            akwargs = []
            for i, arg in enumerate(args):
                arg = formatters.get(i, repr)(arg)  # type: ignore[index]
                akwargs.append(arg)
            for key, val in list(kwargs.items()):
                val = formatters.get(key, repr)(val)  # type: ignore[index]
                akwargs.append(f"{key}={val}")
            LOG.debug(r"%s(%s)", fun.__name__, ", ".join(akwargs))
            result = fun(*args, **kwargs)
            returns = formatters.get("returns", repr)(result)
            LOG.debug(" return %s", returns)
            return result

        return decorated

    return decorator


def _not_logged(*args, **kwargs) -> Decorator:
    return lambda fun: fun


logged: Callable[..., Decorator] = (
    _logged if LOG.isEnabledFor(logging.DEBUG) else _not_logged
)


################################################################
# Profiling

# (fun, arg) -> count
PROFILE_COUNTERS = defaultdict(lambda: 0)


def profile_engine():
    counts = [
        (count, fun.__name__, arg)
        for ((fun, arg), count) in list(PROFILE_COUNTERS.items())
    ]
    counts.sort(reverse=True)
    sys.stderr.write("{: >10} {: >10} {}\n".format("count", "fun", "arg"))
    sys.stderr.write("-" * 32 + "\n")
    for count, fun, arg in counts:
        sys.stderr.write(f"{count: >10} {fun: >10} {arg}\n")


if int(os.environ.get("POMAGMA_PROFILE_ENGINE", 0)):
    atexit.register(profile_engine)
