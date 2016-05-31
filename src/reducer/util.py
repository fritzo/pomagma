from pomagma.compiler.util import memoize_args
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

LOG = logging.getLogger(__name__)
LOG.setLevel(LOG_LEVELS[pomagma.util.LOG_LEVEL])
LOG.addHandler(logging.StreamHandler())


@memoize_args
def pretty(code, add_parens=False):
    if isinstance(code, str):
        return code
    elif code[0] == 'APP':
        lhs = pretty(code[1])
        rhs = pretty(code[2], True)
        return ('({} {})' if add_parens else '{} {}').format(lhs, rhs)
    elif code[0] == 'JOIN':
        lhs = pretty(code[1], True)
        rhs = pretty(code[2], True)
        return ('({}|{})' if add_parens else '{}|{}').format(lhs, rhs)
    elif code[0] == 'VAR':
        return code[1]
    else:
        raise NotImplementedError(code)
