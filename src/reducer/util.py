from collections import defaultdict
from pomagma.compiler.util import memoize_args
import atexit
import functools
import inspect
import logging
import os
import pomagma.util
import sys


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
                raise ValueError('Incompatible: {} vs {}'.format(result, arg))
    return result


def trool_all(args):
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
        elif arg is None:
            result = None
    return result


def trool_any(args):
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
        elif arg is None:
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


# ----------------------------------------------------------------------------
# Logging

LOG_LEVELS = {
    pomagma.util.LOG_LEVEL_ERROR: logging.ERROR,
    pomagma.util.LOG_LEVEL_WARNING: logging.WARNING,
    pomagma.util.LOG_LEVEL_INFO: logging.INFO,
    pomagma.util.LOG_LEVEL_DEBUG: logging.DEBUG,
}


class IndentingFormatter(logging.Formatter):

    def __init__(self):
        logging.Formatter.__init__(self, '%(indent)s %(message)s')
        self.min_indent = float('inf')

    def format(self, record):
        stack = inspect.stack()
        indent = len(stack)
        if indent < self.min_indent:
            self.min_indent = indent
        indent -= self.min_indent
        record.indent = ' ' * indent
        return logging.Formatter.format(self, record)


LOG = logging.getLogger(__name__)
LOG.setLevel(LOG_LEVELS[pomagma.util.LOG_LEVEL])
handler = logging.StreamHandler()
handler.setFormatter(IndentingFormatter())
LOG.addHandler(handler)


def _logged(*format_args, **format_kwargs):
    formatters = dict(format_kwargs)
    for i, fmt in enumerate(format_args):
        formatters[i] = fmt

    def decorator(fun):

        @functools.wraps(fun)
        def decorated(*args, **kwargs):
            akwargs = []
            for i, arg in enumerate(args):
                arg = formatters.get(i, repr)(arg)
                akwargs.append(arg)
            for key, val in kwargs.iteritems():
                val = formatters.get(key, repr)(val)
                akwargs.append('{}={}'.format(key, val))
            LOG.debug(r'{}({})'.format(fun.__name__, ', '.join(akwargs)))
            result = fun(*args, **kwargs)
            returns = formatters.get('returns', repr)(result)
            LOG.debug(' return {}'.format(returns))
            return result

        return decorated

    return decorator


def _not_logged(*args, **kwargs):
    return lambda fun: fun


logged = _logged if LOG.isEnabledFor(logging.DEBUG) else _not_logged


@memoize_args
def pretty(code, add_parens=False):
    if isinstance(code, str):
        return code
    elif code[0] == 'NVAR':
        return code[1]
    elif code[0] == 'APP':
        lhs = pretty(code[1])
        rhs = pretty(code[2], True)
        mid = '' if lhs.endswith(')') or rhs.startswith('(') else ' '
        return ('({}{}{})' if add_parens else '{}{}{}').format(lhs, mid, rhs)
    elif code[0] == 'JOIN':
        lhs = pretty(code[1])
        rhs = pretty(code[2])
        return ('({}|{})' if add_parens else '{}|{}').format(lhs, rhs)
    elif code[0] == 'QUOTE':
        arg = pretty(code[1])
        return '{{{}}}'.format(arg)
    else:
        raise NotImplementedError(code)


# ----------------------------------------------------------------------------
# Profiling

# (fun, arg) -> count
PROFILE_COUNTERS = defaultdict(lambda: 0)


def profile_engine():
    counts = [
        (count, fun.__name__, arg)
        for ((fun, arg), count) in PROFILE_COUNTERS.iteritems()
    ]
    counts.sort(reverse=True)
    sys.stderr.write('{: >10} {: >10} {}\n'.format('count', 'fun', 'arg'))
    sys.stderr.write('-' * 32 + '\n')
    for count, fun, arg in counts:
        sys.stderr.write('{: >10} {: >10} {}\n'.format(count, fun, arg))


if int(os.environ.get('POMAGMA_PROFILE_ENGINE', 0)):
    atexit.register(profile_engine)
