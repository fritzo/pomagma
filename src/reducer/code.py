from pomagma.compiler.util import memoize_arg
from pomagma.compiler.util import memoize_args

# ----------------------------------------------------------------------------
# Signature

_VAR = intern('VAR')
_APP = intern('APP')
_JOIN = intern('JOIN')
TOP = intern('TOP')
BOT = intern('BOT')
I = intern('I')
K = intern('K')
B = intern('B')
C = intern('C')
S = intern('S')


@memoize_args
def APP(lhs, rhs):
    return (_APP, lhs, rhs)


@memoize_args
def JOIN(lhs, rhs):
    return (_JOIN, lhs, rhs)


@memoize_arg
def VAR(name):
    return (_VAR, intern(name))


def is_var(code):
    return isinstance(code, tuple) and code[0] is _VAR


def is_app(code):
    return isinstance(code, tuple) and code[0] is _APP


def is_join(code):
    return isinstance(code, tuple) and code[0] is _JOIN


@memoize_arg
def free_vars(code):
    if is_var(code):
        return set([code])
    elif is_app(code) or is_join(code):
        return free_vars(code[1]) | free_vars(code[2])
    else:
        return set()


# ----------------------------------------------------------------------------
# Parsing and seralization

def parse(string):
    assert isinstance(string, str), type(string)
    tokens = map(intern, string.split())
    tokens.reverse()
    return _parse_tokens(tokens)


def _parse_tokens(tokens):
    token = tokens.pop()
    if token is _APP:
        lhs = _parse_tokens(tokens)
        rhs = _parse_tokens(tokens)
        return APP(lhs, rhs)
    elif token is _JOIN:
        lhs = _parse_tokens(tokens)
        rhs = _parse_tokens(tokens)
        return JOIN(lhs, rhs)
    else:
        return token


def serialize(code):
    tokens = []
    _serialize_tokens(code, tokens)
    return ' '.join(tokens)


def _serialize_tokens(code, tokens):
    if isinstance(code, str):
        tokens.append(code)
    elif isinstance(code, tuple):
        tokens.append(code[0])
        for arg in code[1:]:
            _serialize_tokens(arg, tokens)
