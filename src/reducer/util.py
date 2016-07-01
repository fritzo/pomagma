from pomagma.compiler.util import memoize_args
import functools
import inspect
import logging
import pomagma.util

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


def logged(*format_args, **format_kwargs):
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
            LOG.debug('return {}'.format(returns))
            return result

        return decorated

    return decorator


@memoize_args
def pretty(code, add_parens=False):
    if isinstance(code, str):
        return code
    elif code[0] == 'VAR':
        return code[1]
    elif code[0] == 'APP':
        lhs = pretty(code[1])
        rhs = pretty(code[2], True)
        mid = '' if lhs.endswith(')') or rhs.startswith('(') else ' '
        return ('({}{}{})' if add_parens else '{}{}{}').format(lhs, mid, rhs)
    elif code[0] == 'JOIN':
        lhs = pretty(code[1], True)
        rhs = pretty(code[2], True)
        return ('({}|{})' if add_parens else '{}|{}').format(lhs, rhs)
    elif code[0] == 'QUOTE':
        arg = pretty(code[1])
        return '{{{}}}'.format(arg)
    else:
        raise NotImplementedError(code)
